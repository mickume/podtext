"""Audio transcription service using MLX-Whisper."""

import warnings
from pathlib import Path

from podtext.core.errors import TranscriptionError
from podtext.core.models import Segment, Transcript


class TranscriptionService:
    """Handles audio transcription with MLX-Whisper."""

    def __init__(self, model: str = "base", skip_language_check: bool = False) -> None:
        """
        Initialize the transcription service.

        Args:
            model: Whisper model to use (tiny, base, small, medium, large)
            skip_language_check: Whether to skip language verification
        """
        self.model = model
        self.skip_language_check = skip_language_check
        self._model_loaded = False

    def transcribe(self, audio_path: Path) -> Transcript:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            Transcript with segments

        Raises:
            TranscriptionError: If transcription fails
        """
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        try:
            import mlx_whisper
        except ImportError as e:
            raise TranscriptionError(
                "mlx-whisper is not installed. Install with: pip install mlx-whisper"
            ) from e

        try:
            # Transcribe with word timestamps for better segmentation
            result = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=f"mlx-community/whisper-{self.model}-mlx",
                verbose=False,
            )
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

        # Extract language
        language = result.get("language", "unknown")

        # Check language if required
        if not self.skip_language_check and language != "en":
            warnings.warn(
                f"Detected language is '{language}', not English. "
                "Use --skip-language-check to suppress this warning.",
                UserWarning,
                stacklevel=2,
            )

        # Convert segments
        segments = []
        for seg in result.get("segments", []):
            segment = Segment(
                text=seg.get("text", "").strip(),
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
            )
            if segment.text:  # Only include non-empty segments
                segments.append(segment)

        # Calculate total duration
        duration = segments[-1].end if segments else 0.0

        return Transcript(
            segments=segments,
            language=language,
            duration=duration,
        )

    def detect_language(self, audio_path: Path) -> str:
        """
        Detect the language of an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            Detected language code

        Raises:
            TranscriptionError: If detection fails
        """
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        try:
            import mlx_whisper
        except ImportError as e:
            raise TranscriptionError(
                "mlx-whisper is not installed. Install with: pip install mlx-whisper"
            ) from e

        try:
            # Use a short transcription to detect language
            result = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=f"mlx-community/whisper-{self.model}-mlx",
                verbose=False,
            )
            return str(result.get("language", "unknown"))
        except Exception as e:
            raise TranscriptionError(f"Language detection failed: {e}") from e
