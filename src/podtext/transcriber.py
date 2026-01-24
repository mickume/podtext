"""MLX-Whisper transcription module."""

import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

from podtext.models import TranscriptionResult


class TranscriptionError(Exception):
    """Exception raised when transcription fails."""

    pass


def _detect_language(result: dict) -> str:
    """Extract detected language from Whisper result."""
    return result.get("language", "en")


def _extract_paragraphs(result: dict) -> list[str]:
    """Extract paragraphs from Whisper segments."""
    segments = result.get("segments", [])

    if not segments:
        text = result.get("text", "")
        return [text] if text else []

    # Group segments into paragraphs based on pauses
    # Whisper segments typically have 'start' and 'end' timestamps
    paragraphs = []
    current_paragraph = []
    last_end = 0.0
    pause_threshold = 2.0  # seconds

    for segment in segments:
        text = segment.get("text", "").strip()
        if not text:
            continue

        start = segment.get("start", 0.0)

        # If there's a significant pause, start a new paragraph
        if current_paragraph and (start - last_end) > pause_threshold:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []

        current_paragraph.append(text)
        last_end = segment.get("end", start)

    # Add remaining text
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return paragraphs


def transcribe(
    audio_path: Path | str,
    model: str = "base",
    skip_language_check: bool = False,
    _whisper_transcribe: Callable[..., dict[str, Any]] | None = None,
) -> TranscriptionResult:
    """
    Transcribe an audio file using MLX-Whisper.

    Args:
        audio_path: Path to the audio file
        model: Whisper model to use (tiny, base, small, medium, large)
        skip_language_check: If True, skip language detection warning
        _whisper_transcribe: Optional callable for testing (replaces mlx_whisper.transcribe)

    Returns:
        TranscriptionResult with text, paragraphs, and detected language

    Raises:
        TranscriptionError: If transcription fails
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    # Use provided transcribe function or import mlx_whisper
    if _whisper_transcribe is None:
        try:
            import mlx_whisper

            transcribe_fn = mlx_whisper.transcribe
        except ImportError as e:
            raise TranscriptionError(
                "mlx_whisper is not installed. Install with: pip install mlx-whisper"
            ) from e
    else:
        transcribe_fn = _whisper_transcribe

    try:
        # Call Whisper transcription
        result = transcribe_fn(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{model}-mlx",
        )
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e

    # Extract language
    language = _detect_language(result)

    # Check for non-English content (unless skipped)
    if not skip_language_check and language != "en":
        warnings.warn(
            f"Detected non-English audio (language: {language}). "
            "Transcription will continue but results may vary.",
            UserWarning,
            stacklevel=2,
        )

    # Extract text and paragraphs
    text = result.get("text", "").strip()
    paragraphs = _extract_paragraphs(result)

    return TranscriptionResult(
        text=text,
        paragraphs=paragraphs,
        language=language,
    )


def transcribe_with_config(
    audio_path: Path | str,
    model: str = "base",
    skip_language_check: bool = False,
) -> TranscriptionResult:
    """
    Transcribe audio using configuration settings.

    This is the main entry point that respects config file settings.

    Args:
        audio_path: Path to the audio file
        model: Whisper model from config
        skip_language_check: Whether to skip language warning

    Returns:
        TranscriptionResult
    """
    return transcribe(
        audio_path=audio_path,
        model=model,
        skip_language_check=skip_language_check,
    )
