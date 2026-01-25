"""Unit tests for the MLX-Whisper transcriber.

Tests transcription functionality, language detection, paragraph extraction,
and error handling.

Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podtext.services.transcriber import (
    DEFAULT_MODEL,
    ENGLISH_LANGUAGE_CODE,
    VALID_MODELS,
    TranscriptionError,
    TranscriptionResult,
    _detect_language,
    _extract_paragraphs,
    _validate_audio_path,
    _validate_model,
    _warn_non_english,
    transcribe,
    transcribe_with_config,
)


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_create_transcription_result(self) -> None:
        """Test creating a TranscriptionResult."""
        result = TranscriptionResult(
            text="Hello world",
            paragraphs=["Hello", "world"],
            language="en",
        )
        assert result.text == "Hello world"
        assert result.paragraphs == ["Hello", "world"]
        assert result.language == "en"

    def test_transcription_result_empty_paragraphs(self) -> None:
        """Test TranscriptionResult with empty paragraphs."""
        result = TranscriptionResult(
            text="",
            paragraphs=[],
            language="en",
        )
        assert result.text == ""
        assert result.paragraphs == []


class TestValidateModel:
    """Tests for _validate_model function."""

    def test_valid_models(self) -> None:
        """Test that all valid models pass validation."""
        for model in VALID_MODELS:
            # Should not raise
            _validate_model(model)

    def test_invalid_model_raises_error(self) -> None:
        """Test that invalid model raises TranscriptionError."""
        with pytest.raises(TranscriptionError) as exc_info:
            _validate_model("invalid_model")
        assert "Invalid Whisper model" in str(exc_info.value)
        assert "invalid_model" in str(exc_info.value)

    def test_default_model_is_valid(self) -> None:
        """Test that the default model is valid."""
        assert DEFAULT_MODEL in VALID_MODELS
        _validate_model(DEFAULT_MODEL)


class TestValidateAudioPath:
    """Tests for _validate_audio_path function."""

    def test_existing_file_passes(self, tmp_path: Path) -> None:
        """Test that existing file passes validation."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")
        # Should not raise
        _validate_audio_path(audio_file)

    def test_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Test that nonexistent file raises TranscriptionError."""
        audio_file = tmp_path / "nonexistent.mp3"
        with pytest.raises(TranscriptionError) as exc_info:
            _validate_audio_path(audio_file)
        assert "Audio file not found" in str(exc_info.value)


class TestExtractParagraphs:
    """Tests for _extract_paragraphs function.
    
    Validates: Requirement 4.3
    """

    def test_empty_segments(self) -> None:
        """Test extracting paragraphs from empty segments."""
        result = _extract_paragraphs([])
        assert result == []

    def test_single_segment(self) -> None:
        """Test extracting paragraphs from single segment."""
        segments = [{"text": "Hello world."}]
        result = _extract_paragraphs(segments)
        assert len(result) == 1
        assert "Hello world." in result[0]

    def test_multiple_segments_grouped(self) -> None:
        """Test that multiple segments are grouped into paragraphs."""
        segments = [
            {"text": "First sentence."},
            {"text": "Second sentence."},
            {"text": "Third sentence."},
            {"text": "Fourth sentence."},
        ]
        result = _extract_paragraphs(segments)
        # Should create at least one paragraph
        assert len(result) >= 1
        # All text should be present
        full_text = " ".join(result)
        assert "First sentence" in full_text
        assert "Fourth sentence" in full_text

    def test_paragraph_breaks_at_sentence_end(self) -> None:
        """Test that paragraphs break at sentence endings."""
        segments = [
            {"text": "First."},
            {"text": "Second."},
            {"text": "Third."},
            {"text": "Fourth."},
            {"text": "Fifth."},
            {"text": "Sixth."},
        ]
        result = _extract_paragraphs(segments)
        # Should have multiple paragraphs
        assert len(result) >= 1

    def test_empty_text_segments_ignored(self) -> None:
        """Test that segments with empty text are ignored."""
        segments = [
            {"text": "Hello."},
            {"text": ""},
            {"text": "   "},
            {"text": "World."},
        ]
        result = _extract_paragraphs(segments)
        full_text = " ".join(result)
        assert "Hello" in full_text
        assert "World" in full_text

    def test_segments_without_text_key(self) -> None:
        """Test handling segments without text key."""
        segments = [
            {"text": "Hello."},
            {"start": 0, "end": 1},  # No text key
            {"text": "World."},
        ]
        result = _extract_paragraphs(segments)
        full_text = " ".join(result)
        assert "Hello" in full_text
        assert "World" in full_text


class TestDetectLanguage:
    """Tests for _detect_language function.
    
    Validates: Requirement 5.1
    """

    def test_detect_english(self) -> None:
        """Test detecting English language."""
        result = {"language": "en", "text": "Hello"}
        language = _detect_language(result)
        assert language == "en"

    def test_detect_non_english(self) -> None:
        """Test detecting non-English language."""
        result = {"language": "es", "text": "Hola"}
        language = _detect_language(result)
        assert language == "es"

    def test_missing_language_defaults_to_english(self) -> None:
        """Test that missing language defaults to English."""
        result = {"text": "Hello"}
        language = _detect_language(result)
        assert language == "en"


class TestWarnNonEnglish:
    """Tests for _warn_non_english function.
    
    Validates: Requirement 5.2
    """

    def test_warning_printed_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that warning is printed to stderr."""
        _warn_non_english("es")
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "es" in captured.err
        assert "not English" in captured.err


class TestTranscribe:
    """Tests for transcribe function.
    
    Validates: Requirements 4.1, 4.2, 4.3, 5.1, 5.2, 5.3
    """

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", False)
    def test_mlx_whisper_not_available(self, tmp_path: Path) -> None:
        """Test error when mlx_whisper is not installed."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe(audio_file)
        assert "mlx-whisper is not installed" in str(exc_info.value)

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_success(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful transcription.
        
        Validates: Requirement 4.1
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Hello world. This is a test.",
            "segments": [
                {"text": "Hello world."},
                {"text": "This is a test."},
            ],
            "language": "en",
        }

        result = transcribe(audio_file)

        assert result.text == "Hello world. This is a test."
        assert result.language == "en"
        assert len(result.paragraphs) >= 1

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_uses_specified_model(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test that transcribe uses the specified model.
        
        Validates: Requirement 4.2
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Test",
            "segments": [],
            "language": "en",
        }

        transcribe(audio_file, model="small")

        mock_mlx_whisper.transcribe.assert_called_once()
        call_args = mock_mlx_whisper.transcribe.call_args
        assert "whisper-small" in call_args.kwargs.get("path_or_hf_repo", "")

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_default_model(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test that transcribe uses default model when not specified.
        
        Validates: Requirement 4.2
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Test",
            "segments": [],
            "language": "en",
        }

        transcribe(audio_file)

        call_args = mock_mlx_whisper.transcribe.call_args
        assert f"whisper-{DEFAULT_MODEL}" in call_args.kwargs.get("path_or_hf_repo", "")

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_extracts_paragraphs(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test that transcribe extracts paragraphs from segments.
        
        Validates: Requirement 4.3
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "First paragraph. Second paragraph.",
            "segments": [
                {"text": "First paragraph."},
                {"text": "Second paragraph."},
            ],
            "language": "en",
        }

        result = transcribe(audio_file)

        assert len(result.paragraphs) >= 1
        full_text = " ".join(result.paragraphs)
        assert "First paragraph" in full_text
        assert "Second paragraph" in full_text

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_detects_language(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test that transcribe detects language.
        
        Validates: Requirement 5.1
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Hola mundo",
            "segments": [],
            "language": "es",
        }

        result = transcribe(audio_file)

        assert result.language == "es"

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_warns_non_english(
        self,
        mock_mlx_whisper: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that transcribe warns for non-English content.
        
        Validates: Requirement 5.2
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Bonjour",
            "segments": [],
            "language": "fr",
        }

        result = transcribe(audio_file)

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "fr" in captured.err
        assert result.language == "fr"

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_no_warning_for_english(
        self,
        mock_mlx_whisper: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that transcribe doesn't warn for English content."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Hello",
            "segments": [],
            "language": "en",
        }

        transcribe(audio_file)

        captured = capsys.readouterr()
        assert "Warning" not in captured.err

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_skip_language_check(
        self,
        mock_mlx_whisper: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that skip_language_check bypasses language detection.
        
        Validates: Requirement 5.3
        """
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Bonjour",
            "segments": [],
            "language": "fr",
        }

        result = transcribe(audio_file, skip_language_check=True)

        # Should not warn even for non-English
        captured = capsys.readouterr()
        assert "Warning" not in captured.err
        # Language should be set to "unknown" when skipped
        assert result.language == "unknown"

    def test_transcribe_invalid_model(self, tmp_path: Path) -> None:
        """Test that invalid model raises error."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe(audio_file, model="invalid")
        assert "Invalid Whisper model" in str(exc_info.value)

    def test_transcribe_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that nonexistent file raises error."""
        audio_file = tmp_path / "nonexistent.mp3"

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe(audio_file)
        assert "Audio file not found" in str(exc_info.value)

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_handles_mlx_error(
        self, mock_mlx_whisper: MagicMock, tmp_path: Path
    ) -> None:
        """Test that transcribe handles mlx_whisper errors."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.side_effect = RuntimeError("MLX error")

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe(audio_file)
        assert "Transcription failed" in str(exc_info.value)


class TestTranscribeWithConfig:
    """Tests for transcribe_with_config function.
    
    Validates: Requirement 4.2
    """

    @patch("podtext.services.transcriber.transcribe")
    def test_uses_provided_model(self, mock_transcribe: MagicMock, tmp_path: Path) -> None:
        """Test that provided model is used."""
        audio_file = tmp_path / "test.mp3"
        mock_transcribe.return_value = TranscriptionResult(
            text="Test", paragraphs=[], language="en"
        )

        transcribe_with_config(audio_file, model="large")

        mock_transcribe.assert_called_once_with(audio_file, "large", False)

    @patch("podtext.services.transcriber.transcribe")
    def test_uses_default_model_when_none(
        self, mock_transcribe: MagicMock, tmp_path: Path
    ) -> None:
        """Test that default model is used when None provided."""
        audio_file = tmp_path / "test.mp3"
        mock_transcribe.return_value = TranscriptionResult(
            text="Test", paragraphs=[], language="en"
        )

        transcribe_with_config(audio_file, model=None)

        mock_transcribe.assert_called_once_with(audio_file, DEFAULT_MODEL, False)

    @patch("podtext.services.transcriber.transcribe")
    def test_passes_skip_language_check(
        self, mock_transcribe: MagicMock, tmp_path: Path
    ) -> None:
        """Test that skip_language_check is passed through."""
        audio_file = tmp_path / "test.mp3"
        mock_transcribe.return_value = TranscriptionResult(
            text="Test", paragraphs=[], language="en"
        )

        transcribe_with_config(audio_file, skip_language_check=True)

        mock_transcribe.assert_called_once_with(audio_file, DEFAULT_MODEL, True)


class TestAllValidModels:
    """Tests to ensure all valid models work correctly.
    
    Validates: Requirement 4.2
    """

    @patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True)
    @patch("podtext.services.transcriber.mlx_whisper")
    @pytest.mark.parametrize("model", list(VALID_MODELS))
    def test_all_valid_models_accepted(
        self, mock_mlx_whisper: MagicMock, model: str, tmp_path: Path
    ) -> None:
        """Test that all valid models are accepted."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        mock_mlx_whisper.transcribe.return_value = {
            "text": "Test",
            "segments": [],
            "language": "en",
        }

        # Should not raise
        result = transcribe(audio_file, model=model)
        assert result.text == "Test"

        # Verify correct model path was used
        call_args = mock_mlx_whisper.transcribe.call_args
        assert f"whisper-{model}" in call_args.kwargs.get("path_or_hf_repo", "")
