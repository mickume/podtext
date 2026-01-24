"""Media file downloader for podcast episodes.

Downloads audio files from URLs and stores them in the configured directory.
"""

from pathlib import Path
from urllib.parse import urlparse
import httpx


class DownloadError(Exception):
    """Error downloading media file."""

    pass


def _get_filename_from_url(url: str) -> str:
    """Extract a filename from a URL."""
    parsed = urlparse(url)
    path = parsed.path
    if path:
        filename = Path(path).name
        if filename:
            return filename
    return "episode.mp3"


def download_media(url: str, dest_dir: Path) -> Path:
    """Download media file from URL to destination directory.

    Args:
        url: URL of the media file to download.
        dest_dir: Directory to store the downloaded file.

    Returns:
        Path to the downloaded file.

    Raises:
        DownloadError: If the download fails.
    """
    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename
    filename = _get_filename_from_url(url)
    dest_path = dest_dir / filename

    # Handle duplicate filenames
    counter = 1
    original_stem = dest_path.stem
    original_suffix = dest_path.suffix
    while dest_path.exists():
        dest_path = dest_dir / f"{original_stem}_{counter}{original_suffix}"
        counter += 1

    try:
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

    except httpx.HTTPStatusError as e:
        raise DownloadError(f"Download failed with status {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise DownloadError(f"Failed to connect: {e}") from e
    except OSError as e:
        raise DownloadError(f"Failed to write file: {e}") from e

    return dest_path


def cleanup_media(file_path: Path) -> None:
    """Delete a media file.

    Args:
        file_path: Path to the file to delete.
    """
    if file_path.exists():
        file_path.unlink()
