"""MLX-Whisper transcriber for Podtext.

Transcribes audio files using MLX-Whisper (optimized for Apple Silicon).
Extracts paragraph boundaries from Whisper's built-in segmentation and
performs language detection with warnings for non-English content.

Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3
"""

from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Try to import mlx_whisper, but allow graceful fallback for testing
try:
    import mlx_whisper

    MLX_WHISPER_AVAILABLE = True
except ImportError:
    mlx_whisper = None  # type: ignore[assignment]
    MLX_WHISPER_AVAILABLE = False

if TYPE_CHECKING:
    pass

# Default Whisper model
DEFAULT_MODEL = "base"

# Valid Whisper model names
VALID_MODELS = {"tiny", "base", "small", "medium", "large"}

# Mapping from simple model names to Hugging Face repo paths
# The mlx-community models use the format: whisper-{size}.en-mlx
MODEL_REPO_MAP = {
    "tiny": "mlx-community/whisper-tiny.en-mlx",
    "base": "mlx-community/whisper-base.en-mlx",
    "small": "mlx-community/whisper-small.en-mlx",
    "medium": "mlx-community/whisper-medium.en-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
}

# Language code for English
ENGLISH_LANGUAGE_CODE = "en"


class TranscriptionError(Exception):
    """Raised when transcription fails.

    Validates: Requirements 4.1
    """


@dataclass
class TranscriptionResult:
    """Result of audio transcription.

    Attributes:
        text: The full transcribed text.
        paragraphs: List of paragraph strings extracted from Whisper segments.
        language: Detected language code (e.g., 'en' for English).

    Validates: Requirements 4.1, 4.3, 5.1
    """

    text: str
    paragraphs: list[str]
    language: str


def _check_mlx_whisper_available() -> None:
    """Check if mlx_whisper is available.

    Raises:
        TranscriptionError: If mlx_whisper is not installed.
    """
    if not MLX_WHISPER_AVAILABLE:
        raise TranscriptionError(
            "mlx-whisper is not installed. "
            "Install it with: pip install mlx-whisper"
        )


def _validate_model(model: str) -> None:
    """Validate the Whisper model name.

    Args:
        model: The model name to validate.

    Raises:
        TranscriptionError: If the model name is invalid.
    """
    if model not in VALID_MODELS:
        raise TranscriptionError(
            f"Invalid Whisper model '{model}'. "
            f"Valid options: {', '.join(sorted(VALID_MODELS))}"
        )


def _validate_audio_path(audio_path: Path) -> None:
    """Validate that the audio file exists.

    Args:
        audio_path: Path to the audio file.

    Raises:
        TranscriptionError: If the file doesn't exist.
    """
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")


def _extract_paragraphs(segments: list[dict[str, Any]]) -> list[str]:
    """Extract paragraph boundaries from Whisper segments.

    Uses Whisper's built-in segmentation to create paragraphs.
    Groups consecutive segments into paragraphs based on natural
    breaks in the audio (pauses, sentence endings).

    Args:
        segments: List of segment dictionaries from Whisper output.

    Returns:
        List of paragraph strings.

    Validates: Requirements 4.3
    """
    if not segments:
        return []

    paragraphs: list[str] = []
    current_paragraph: list[str] = []

    for segment in segments:
        text = segment.get("text", "").strip()
        if not text:
            continue

        current_paragraph.append(text)

        # Create paragraph breaks at natural boundaries
        # Whisper segments often end at sentence boundaries
        # We group ~3-5 segments per paragraph for readability
        if len(current_paragraph) >= 4 or text.endswith((".", "!", "?")):
            if len(current_paragraph) >= 2:
                paragraph_text = " ".join(current_paragraph)
                paragraphs.append(paragraph_text)
                current_paragraph = []

    # Add any remaining text as final paragraph
    if current_paragraph:
        paragraph_text = " ".join(current_paragraph)
        paragraphs.append(paragraph_text)

    return paragraphs


def _detect_language(result: dict[str, Any]) -> str:
    """Extract detected language from Whisper result.

    Args:
        result: The Whisper transcription result dictionary.

    Returns:
        Language code string (e.g., 'en' for English).

    Validates: Requirements 5.1
    """
    # mlx_whisper returns language in the result dict
    return result.get("language", "en")


def _warn_non_english(language: str) -> None:
    """Display warning for non-English content.

    Args:
        language: The detected language code.

    Validates: Requirements 5.2
    """
    print(
        f"Warning: Detected language '{language}' is not English. "
        "Transcription will continue, but results may vary.",
        file=sys.stderr,
    )


def transcribe(
    audio_path: Path,
    model: str = DEFAULT_MODEL,
    skip_language_check: bool = False,
) -> TranscriptionResult:
    """Transcribe audio file using MLX-Whisper.

    Transcribes the audio file at the given path using the specified
    Whisper model. Extracts paragraph boundaries from Whisper's
    built-in segmentation and detects the audio language.

    Args:
        audio_path: Path to the audio file to transcribe.
        model: Whisper model to use (tiny, base, small, medium, large).
            Defaults to 'base'.
        skip_language_check: If True, bypass language detection entirely.
            Defaults to False.

    Returns:
        TranscriptionResult containing the transcribed text, paragraphs,
        and detected language.

    Raises:
        TranscriptionError: If transcription fails for any reason.

    Validates: Requirements 4.1, 4.2, 4.3, 5.1, 5.2, 5.3
    """
    # Validate inputs
    _check_mlx_whisper_available()
    _validate_model(model)
    _validate_audio_path(audio_path)

    try:
        # Perform transcription using mlx_whisper
        # The transcribe function returns a dict with 'text', 'segments', 'language'
        # Get the correct Hugging Face repo path for the model
        repo_path = MODEL_REPO_MAP.get(model, f"mlx-community/whisper-{model}.en-mlx")
        
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=repo_path,
        )

        # Extract full text
        text = result.get("text", "").strip()

        # Extract paragraphs from segments
        segments = result.get("segments", [])
        paragraphs = _extract_paragraphs(segments)

        # Handle language detection
        if skip_language_check:
            # Bypass language detection entirely (Requirement 5.3)
            language = "unknown"
        else:
            # Detect language (Requirement 5.1)
            language = _detect_language(result)

            # Warn if not English (Requirement 5.2)
            if language != ENGLISH_LANGUAGE_CODE:
                _warn_non_english(language)

        return TranscriptionResult(
            text=text,
            paragraphs=paragraphs,
            language=language,
        )

    except Exception as e:
        if isinstance(e, TranscriptionError):
            raise
        raise TranscriptionError(f"Transcription failed: {e}") from e


def transcribe_with_config(
    audio_path: Path,
    model: str | None = None,
    skip_language_check: bool = False,
) -> TranscriptionResult:
    """Transcribe audio file using model from configuration.

    Convenience function that uses the configured Whisper model
    if no model is explicitly specified.

    Args:
        audio_path: Path to the audio file to transcribe.
        model: Whisper model to use. If None, uses default.
        skip_language_check: If True, bypass language detection.

    Returns:
        TranscriptionResult containing the transcribed text.

    Raises:
        TranscriptionError: If transcription fails.

    Validates: Requirements 4.2
    """
    effective_model = model if model is not None else DEFAULT_MODEL
    return transcribe(audio_path, effective_model, skip_language_check)


def handle_transcription_error(error: TranscriptionError) -> None:
    """Display transcription error message and exit gracefully.

    Args:
        error: The transcription error that occurred.

    Validates: Requirements 4.1
    """
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)
