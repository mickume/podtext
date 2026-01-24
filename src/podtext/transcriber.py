"""Audio transcription using MLX-Whisper.

Transcribes podcast audio files using the MLX-Whisper library,
which is optimized for Apple Silicon.
"""

import warnings
from pathlib import Path

from .models import TranscriptionResult


class TranscriptionError(Exception):
    """Error during transcription."""

    pass


# Global flag for testing - allows mocking the whisper module
_whisper_module = None


def _get_whisper():
    """Get the mlx_whisper module, supporting test mocking."""
    global _whisper_module
    if _whisper_module is not None:
        return _whisper_module
    import mlx_whisper
    return mlx_whisper


def _set_whisper_module(module):
    """Set a mock whisper module for testing."""
    global _whisper_module
    _whisper_module = module


def _reset_whisper_module():
    """Reset to the real whisper module."""
    global _whisper_module
    _whisper_module = None


def transcribe(
    audio_path: Path,
    model: str = "base",
    skip_language_check: bool = False,
) -> TranscriptionResult:
    """Transcribe audio file using MLX-Whisper.

    Args:
        audio_path: Path to the audio file.
        model: Whisper model to use (tiny, base, small, medium, large).
        skip_language_check: If True, skip language detection warning.

    Returns:
        TranscriptionResult with text, paragraphs, and detected language.

    Raises:
        TranscriptionError: If transcription fails.
    """
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    whisper = _get_whisper()

    try:
        # Transcribe with word-level timestamps for segmentation
        result = whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{model}-mlx",
        )
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e

    # Extract text and language
    text = result.get("text", "").strip()
    language = result.get("language", "unknown")

    # Check language and warn if not English
    if not skip_language_check and language != "en":
        warnings.warn(
            f"Detected language '{language}' is not English. "
            "Transcription quality may vary.",
            UserWarning,
        )

    # Extract paragraphs from segments
    segments = result.get("segments", [])
    paragraphs = _segments_to_paragraphs(segments)

    return TranscriptionResult(
        text=text,
        paragraphs=paragraphs,
        language=language,
    )


def _segments_to_paragraphs(segments: list[dict]) -> list[str]:
    """Convert Whisper segments to paragraphs.

    Groups segments into paragraphs based on pauses and content.
    """
    if not segments:
        return []

    paragraphs = []
    current_paragraph = []
    last_end_time = 0.0

    # Threshold for paragraph break (seconds of silence)
    PARAGRAPH_BREAK_THRESHOLD = 1.5

    for segment in segments:
        start_time = segment.get("start", 0.0)
        end_time = segment.get("end", 0.0)
        text = segment.get("text", "").strip()

        if not text:
            continue

        # Check for paragraph break based on pause duration
        if current_paragraph and (start_time - last_end_time) > PARAGRAPH_BREAK_THRESHOLD:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []

        current_paragraph.append(text)
        last_end_time = end_time

    # Add remaining text as final paragraph
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return paragraphs


def detect_language(audio_path: Path) -> str:
    """Detect the language of an audio file.

    Args:
        audio_path: Path to the audio file.

    Returns:
        ISO language code (e.g., "en", "es", "fr").
    """
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    whisper = _get_whisper()

    try:
        # Use a short transcription to detect language
        result = whisper.transcribe(
            str(audio_path),
            path_or_hf_repo="mlx-community/whisper-tiny-mlx",
        )
        return result.get("language", "unknown")
    except Exception:
        return "unknown"
