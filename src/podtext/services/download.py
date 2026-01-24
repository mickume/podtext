"""Media download service."""

import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from podtext.core.errors import DownloadError
from podtext.core.models import Episode

# Video file extensions that need audio extraction
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".flv"}


class DownloadService:
    """Handles media file downloads and management."""

    def __init__(self, download_dir: Path, timeout: float = 600.0) -> None:
        """
        Initialize the download service.

        Args:
            download_dir: Directory to save downloaded files
            timeout: HTTP timeout in seconds (default 10 minutes)
        """
        self.download_dir = download_dir
        self.timeout = timeout
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, episode: Episode) -> Path:
        """
        Download episode media file.

        Args:
            episode: Episode to download

        Returns:
            Path to the downloaded file

        Raises:
            DownloadError: If download fails
        """
        if not episode.media_url:
            raise DownloadError(f"No media URL for episode: {episode.title}")

        # Determine filename from URL
        filename = self._get_filename_from_url(episode.media_url)
        output_path = self.download_dir / filename

        try:
            with (
                httpx.Client(timeout=self.timeout, follow_redirects=True) as client,
                client.stream("GET", episode.media_url) as response,
            ):
                response.raise_for_status()

                # Write to file
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        except httpx.HTTPError as e:
            raise DownloadError(f"Failed to download media: {e}") from e
        except OSError as e:
            raise DownloadError(f"Failed to save media file: {e}") from e

        return output_path

    def extract_audio(self, media_path: Path) -> Path:
        """
        Extract audio from video file if needed.

        Args:
            media_path: Path to the media file

        Returns:
            Path to audio file (may be same as input if already audio)

        Raises:
            DownloadError: If extraction fails
        """
        if not self._is_video(media_path):
            return media_path

        output_path = media_path.with_suffix(".mp3")

        try:
            import ffmpeg

            (
                ffmpeg.input(str(media_path))
                .output(str(output_path), acodec="libmp3lame", audio_bitrate="192k")
                .overwrite_output()
                .run(quiet=True)
            )
        except Exception as e:
            raise DownloadError(f"Failed to extract audio: {e}") from e

        return output_path

    def cleanup(self, path: Path) -> None:
        """
        Remove a downloaded file.

        Args:
            path: Path to file to delete
        """
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass  # Ignore cleanup errors

    def _get_filename_from_url(self, url: str) -> str:
        """Extract a safe filename from URL."""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = Path(path).name

        # Remove query strings that might be part of filename
        filename = filename.split("?")[0]

        # Sanitize filename
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Ensure we have an extension
        if not Path(filename).suffix:
            # Try to guess from content type
            content_type = mimetypes.guess_type(url)[0]
            if content_type:
                ext = mimetypes.guess_extension(content_type) or ".mp3"
                filename += ext
            else:
                filename += ".mp3"

        # Limit length
        if len(filename) > 200:
            name = Path(filename).stem[:190]
            ext = Path(filename).suffix
            filename = name + ext

        return filename

    def _is_video(self, path: Path) -> bool:
        """Check if file is a video format."""
        return path.suffix.lower() in VIDEO_EXTENSIONS
