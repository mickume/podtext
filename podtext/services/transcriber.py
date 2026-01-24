"""Transcription service using MLX-Whisper."""

import tempfile
from pathlib import Path

import httpx
import mlx_whisper

from podtext.config.manager import Config
from podtext.models.transcript import Transcript


class TranscriptionError(Exception):
    """Exception raised for transcription errors."""

    pass


class TranscriberService:
    """Service for downloading and transcribing podcast episodes."""

    def __init__(self, config: Config):
        """Initialize the transcriber service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.whisper_model = f"mlx-community/whisper-{config.whisper_model}-mlx"

    def download_media(self, url: str, output_path: Path | None = None) -> Path:
        """Download a media file from URL.

        Args:
            url: Media file URL
            output_path: Optional path to save to (uses temp file if not provided)

        Returns:
            Path to downloaded file

        Raises:
            TranscriptionError: If download fails
        """
        if output_path is None:
            # Determine extension from URL
            ext = self._get_extension(url)
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            output_path = Path(temp_path)

        try:
            with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()

                    with open(output_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

        except httpx.TimeoutException as e:
            raise TranscriptionError(f"Download timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            raise TranscriptionError(f"Download failed: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TranscriptionError(f"Download failed: {e}") from e

        return output_path

    def transcribe(self, media_path: Path, language: str | None = None) -> Transcript:
        """Transcribe a media file.

        Args:
            media_path: Path to the media file
            language: Optional language code (auto-detected if not provided)

        Returns:
            Transcript object with text and segments

        Raises:
            TranscriptionError: If transcription fails
        """
        if not media_path.exists():
            raise TranscriptionError(f"Media file not found: {media_path}")

        try:
            result = mlx_whisper.transcribe(
                str(media_path),
                path_or_hf_repo=self.whisper_model,
                language=language,
            )
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

        return self._parse_result(result)

    def cleanup_media(self, media_path: Path) -> None:
        """Delete a media file if cleanup is enabled.

        Args:
            media_path: Path to the media file
        """
        if self.config.cleanup_media and media_path.exists():
            try:
                media_path.unlink()
            except OSError:
                pass  # Ignore cleanup errors

    def detect_language(self, media_path: Path) -> str:
        """Detect the language of a media file.

        Args:
            media_path: Path to the media file

        Returns:
            Detected language code
        """
        try:
            result = mlx_whisper.transcribe(
                str(media_path),
                path_or_hf_repo=self.whisper_model,
                # Only process first 30 seconds for language detection
            )
            return result.get("language", "en")
        except Exception:
            return "en"

    def _parse_result(self, result: dict) -> Transcript:
        """Parse MLX-Whisper result into Transcript object."""
        text = result.get("text", "").strip()
        language = result.get("language", "en")
        segments = result.get("segments", [])

        # Extract paragraphs from segments
        paragraphs = self._create_paragraphs(segments)

        return Transcript(
            text=text,
            paragraphs=paragraphs,
            language=language,
            segments=segments,
        )

    def _create_paragraphs(self, segments: list[dict]) -> list[str]:
        """Create paragraphs from transcription segments.

        Groups segments into paragraphs based on pauses and punctuation.
        """
        if not segments:
            return []

        paragraphs = []
        current_paragraph: list[str] = []
        last_end_time = 0.0

        for segment in segments:
            text = segment.get("text", "").strip()
            if not text:
                continue

            start_time = segment.get("start", 0.0)

            # Start new paragraph if there's a significant pause (> 2 seconds)
            # or if the previous segment ended with terminal punctuation
            gap = start_time - last_end_time
            should_break = gap > 2.0

            if current_paragraph and should_break:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []

            current_paragraph.append(text)
            last_end_time = segment.get("end", start_time)

        # Add final paragraph
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))

        return paragraphs

    def _get_extension(self, url: str) -> str:
        """Extract file extension from URL."""
        url_lower = url.lower()
        for ext in [".mp3", ".m4a", ".mp4", ".wav", ".webm"]:
            if ext in url_lower:
                return ext
        return ".mp3"  # Default to mp3
