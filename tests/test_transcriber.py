"""Tests for MLX-Whisper transcriber.

Feature: podtext
Property 7: Config Model Propagation
Property 9: Language Check Bypass
"""

import pytest
import warnings
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from podtext.transcriber import (
    transcribe,
    TranscriptionError,
    _segments_to_paragraphs,
    _set_whisper_module,
    _reset_whisper_module,
)
from podtext.models import TranscriptionResult


@pytest.fixture
def mock_whisper():
    """Fixture that provides a mock whisper module."""
    mock = MagicMock()
    mock.transcribe.return_value = {
        "text": "Hello world",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": "world"},
        ]
    }
    _set_whisper_module(mock)
    yield mock
    _reset_whisper_module()


@pytest.fixture
def audio_file(temp_dir):
    """Create a fake audio file for testing."""
    audio_path = temp_dir / "test.mp3"
    audio_path.write_bytes(b"fake audio content")
    return audio_path


class TestSegmentsToParagraphs:
    """Tests for segment to paragraph conversion."""

    def test_empty_segments(self):
        """Empty segments produce empty paragraphs."""
        assert _segments_to_paragraphs([]) == []

    def test_single_segment(self):
        """Single segment produces single paragraph."""
        segments = [{"start": 0.0, "end": 1.0, "text": "Hello world"}]
        result = _segments_to_paragraphs(segments)
        assert result == ["Hello world"]

    def test_consecutive_segments(self):
        """Consecutive segments without pause form single paragraph."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.1, "end": 2.0, "text": "world"},
        ]
        result = _segments_to_paragraphs(segments)
        assert result == ["Hello world"]

    def test_pause_creates_paragraph_break(self):
        """Long pause creates paragraph break."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "First paragraph."},
            {"start": 3.0, "end": 4.0, "text": "Second paragraph."},
        ]
        result = _segments_to_paragraphs(segments)
        assert result == ["First paragraph.", "Second paragraph."]

    def test_empty_text_segments_skipped(self):
        """Segments with empty text are skipped."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": ""},
            {"start": 2.0, "end": 3.0, "text": "world"},
        ]
        result = _segments_to_paragraphs(segments)
        assert result == ["Hello world"]


class TestTranscribeBasics:
    """Basic transcription tests."""

    def test_transcribe_returns_result(self, mock_whisper, audio_file):
        """Transcribe returns TranscriptionResult."""
        result = transcribe(audio_file)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"

    def test_transcribe_nonexistent_file(self, mock_whisper, temp_dir):
        """Transcribe raises error for nonexistent file."""
        with pytest.raises(TranscriptionError, match="not found"):
            transcribe(temp_dir / "nonexistent.mp3")

    def test_transcribe_handles_whisper_error(self, mock_whisper, audio_file):
        """Transcribe handles whisper errors."""
        mock_whisper.transcribe.side_effect = RuntimeError("Model error")

        with pytest.raises(TranscriptionError, match="Transcription failed"):
            transcribe(audio_file)


class TestProperty7ConfigModelPropagation:
    """Property 7: Config Model Propagation.

    For any configuration with whisper.model set to M,
    the transcription function SHALL be called with model parameter M.

    Validates: Requirements 4.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(model=st.sampled_from(["tiny", "base", "small", "medium", "large"]))
    def test_model_passed_to_whisper(self, mock_whisper, audio_file, model):
        """Configured model is passed to whisper.transcribe."""
        # Reset mock to get clean call tracking for this iteration
        mock_whisper.transcribe.reset_mock()

        transcribe(audio_file, model=model)

        # Verify whisper was called with the correct model
        mock_whisper.transcribe.assert_called_once()
        call_args = mock_whisper.transcribe.call_args
        assert f"whisper-{model}-mlx" in call_args.kwargs.get("path_or_hf_repo", "")

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        model1=st.sampled_from(["tiny", "base", "small"]),
        model2=st.sampled_from(["medium", "large"]),
    )
    def test_different_models_produce_different_calls(self, mock_whisper, audio_file, model1, model2):
        """Different model configurations produce different whisper calls."""
        # First call
        transcribe(audio_file, model=model1)
        first_call = mock_whisper.transcribe.call_args

        mock_whisper.reset_mock()

        # Second call with different model
        transcribe(audio_file, model=model2)
        second_call = mock_whisper.transcribe.call_args

        # Calls should use different models
        assert first_call.kwargs["path_or_hf_repo"] != second_call.kwargs["path_or_hf_repo"]


class TestProperty9LanguageCheckBypass:
    """Property 9: Language Check Bypass.

    For any transcription operation with skip-language-check flag set,
    the language detection function SHALL not be called.

    Note: In our implementation, language detection is part of transcription,
    so we verify that no warning is issued when skip_language_check=True.

    Validates: Requirements 5.3
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(language=st.sampled_from(["es", "fr", "de", "ja", "zh"]))
    def test_no_warning_when_skip_language_check(self, mock_whisper, audio_file, language):
        """No warning is issued when skip_language_check=True."""
        mock_whisper.transcribe.return_value = {
            "text": "Content in another language",
            "language": language,
            "segments": [],
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = transcribe(audio_file, skip_language_check=True)

            # No language warnings should be issued
            language_warnings = [x for x in w if "language" in str(x.message).lower()]
            assert len(language_warnings) == 0

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(language=st.sampled_from(["es", "fr", "de", "ja", "zh"]))
    def test_warning_when_not_skipping_language_check(self, mock_whisper, audio_file, language):
        """Warning is issued for non-English when skip_language_check=False."""
        mock_whisper.transcribe.return_value = {
            "text": "Content in another language",
            "language": language,
            "segments": [],
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = transcribe(audio_file, skip_language_check=False)

            # Should have language warning
            language_warnings = [x for x in w if "language" in str(x.message).lower()]
            assert len(language_warnings) == 1

    def test_no_warning_for_english(self, mock_whisper, audio_file):
        """No warning for English content."""
        mock_whisper.transcribe.return_value = {
            "text": "English content",
            "language": "en",
            "segments": [],
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = transcribe(audio_file, skip_language_check=False)

            language_warnings = [x for x in w if "language" in str(x.message).lower()]
            assert len(language_warnings) == 0
