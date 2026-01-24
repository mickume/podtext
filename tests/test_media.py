"""Tests for media download and transcription modules.

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from hypothesis import given, settings, strategies as st

from podtext.downloader import (
    DownloadError,
    cleanup_media_file,
    download_media,
)
from podtext.transcriber import (
    TranscriptionError,
    TranscriptionResult,
    transcribe,
    _extract_paragraphs,
)


class TestMediaStorageLocation:
    """
    Property 5: Media Storage Location

    For any configuration with media_dir set to path P,
    downloaded media files SHALL be stored within path P.

    Validates: Requirements 3.2
    """

    @settings(max_examples=100)
    @given(
        subdir=st.text(
            min_size=1,
            max_size=20,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        ),
        filename=st.text(
            min_size=1,
            max_size=20,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        ),
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_downloaded_files_stored_in_configured_directory(
        self,
        subdir: str,
        filename: str,
    ) -> None:
        """Property 5: Downloaded files are stored in the configured media_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = Path(tmpdir) / subdir
            full_filename = f"{filename}.mp3"

            # Mock the download
            respx.get("https://example.com/audio.mp3").mock(
                return_value=httpx.Response(200, content=b"fake audio data")
            )

            result_path = await download_media(
                "https://example.com/audio.mp3",
                dest_dir=media_dir,
                filename=full_filename,
            )

            # File should be within media_dir
            assert result_path.parent == media_dir, (
                f"File should be in {media_dir}, got {result_path.parent}"
            )
            assert result_path.exists(), "Downloaded file should exist"
            assert result_path.name == full_filename, (
                f"Filename should be {full_filename}, got {result_path.name}"
            )


class TestTemporaryFileCleanup:
    """
    Property 6: Temporary File Cleanup

    For any transcription operation with temp_storage=true,
    after completion the media file SHALL not exist on disk.

    Validates: Requirements 3.3
    """

    @settings(max_examples=100)
    @given(
        content=st.binary(min_size=1, max_size=1000),
    )
    def test_cleanup_removes_file(self, content: bytes) -> None:
        """Property 6: cleanup_media_file removes the file from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_file.mp3"

            # Create file with content
            with open(file_path, "wb") as f:
                f.write(content)

            assert file_path.exists(), "File should exist before cleanup"

            # Cleanup
            result = cleanup_media_file(file_path)

            assert result is True, "Cleanup should return True"
            assert not file_path.exists(), "File should not exist after cleanup"

    def test_cleanup_nonexistent_file_returns_false(self) -> None:
        """Cleanup of non-existent file should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nonexistent.mp3"

            result = cleanup_media_file(file_path)

            assert result is False


class TestConfigModelPropagation:
    """
    Property 7: Config Model Propagation

    For any configuration with whisper.model set to M,
    the transcription function SHALL be called with model parameter M.

    Validates: Requirements 4.2
    """

    @settings(max_examples=100)
    @given(
        model=st.sampled_from(["tiny", "base", "small", "medium", "large"]),
    )
    def test_transcribe_uses_configured_model(self, model: str) -> None:
        """Property 7: Transcription uses the model specified in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy audio file
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.write_bytes(b"fake audio")

            # Mock whisper transcribe function
            mock_transcribe = MagicMock(return_value={
                "text": "Hello world",
                "language": "en",
                "segments": [],
            })

            result = transcribe(
                audio_path=audio_path,
                model=model,
                _whisper_transcribe=mock_transcribe,
            )

            # Verify model was passed correctly
            mock_transcribe.assert_called_once()
            call_kwargs = mock_transcribe.call_args
            assert f"whisper-{model}-mlx" in call_kwargs.kwargs["path_or_hf_repo"], (
                f"Expected model '{model}' in path, got {call_kwargs}"
            )


class TestLanguageCheckBypass:
    """
    Property 9: Language Check Bypass

    For any transcription operation with skip-language-check flag set,
    the language detection function SHALL not trigger a warning.

    Validates: Requirements 5.3
    """

    @settings(max_examples=100)
    @given(
        language=st.sampled_from(["fr", "de", "es", "ja", "zh", "ru", "ar"]),
    )
    def test_skip_language_check_suppresses_warning(self, language: str) -> None:
        """Property 9: No warning when skip_language_check is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.write_bytes(b"fake audio")

            mock_transcribe = MagicMock(return_value={
                "text": "Bonjour monde",
                "language": language,
                "segments": [],
            })

            # With skip_language_check=True, no warning should be raised
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                result = transcribe(
                    audio_path=audio_path,
                    model="base",
                    skip_language_check=True,
                    _whisper_transcribe=mock_transcribe,
                )

                # No UserWarning about language should be present
                language_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, UserWarning)
                    and "non-English" in str(warning.message)
                ]
                assert len(language_warnings) == 0, (
                    "No language warning should be raised when skip_language_check=True"
                )

    def test_language_warning_raised_for_non_english(self) -> None:
        """Warning should be raised for non-English when skip_language_check=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.write_bytes(b"fake audio")

            mock_transcribe = MagicMock(return_value={
                "text": "Bonjour monde",
                "language": "fr",
                "segments": [],
            })

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                result = transcribe(
                    audio_path=audio_path,
                    model="base",
                    skip_language_check=False,
                    _whisper_transcribe=mock_transcribe,
                )

                # Warning should be raised
                language_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, UserWarning)
                    and "non-English" in str(warning.message)
                ]
                assert len(language_warnings) == 1, (
                    "Language warning should be raised for non-English audio"
                )

    def test_no_warning_for_english_content(self) -> None:
        """No warning for English content regardless of skip_language_check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.write_bytes(b"fake audio")

            mock_transcribe = MagicMock(return_value={
                "text": "Hello world",
                "language": "en",
                "segments": [],
            })

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                result = transcribe(
                    audio_path=audio_path,
                    model="base",
                    skip_language_check=False,
                    _whisper_transcribe=mock_transcribe,
                )

                language_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, UserWarning)
                    and "non-English" in str(warning.message)
                ]
                assert len(language_warnings) == 0


class TestDownloadErrorHandling:
    """Tests for download error handling."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_http_error(self) -> None:
        """HTTP errors should raise DownloadError."""
        respx.get("https://example.com/audio.mp3").mock(
            return_value=httpx.Response(404)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(DownloadError) as exc_info:
                await download_media(
                    "https://example.com/audio.mp3",
                    dest_dir=tmpdir,
                )

            assert "404" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_connection_error(self) -> None:
        """Connection errors should raise DownloadError."""
        respx.get("https://example.com/audio.mp3").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(DownloadError) as exc_info:
                await download_media(
                    "https://example.com/audio.mp3",
                    dest_dir=tmpdir,
                )

            assert "Failed to connect" in str(exc_info.value)


class TestTranscriptionErrorHandling:
    """Tests for transcription error handling."""

    def test_transcribe_missing_file(self) -> None:
        """Missing audio file should raise TranscriptionError."""
        with pytest.raises(TranscriptionError) as exc_info:
            transcribe("/nonexistent/audio.mp3")

        assert "not found" in str(exc_info.value)

    def test_transcribe_whisper_failure(self) -> None:
        """Whisper failure should raise TranscriptionError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.write_bytes(b"fake audio")

            mock_transcribe = MagicMock(side_effect=RuntimeError("Whisper failed"))

            with pytest.raises(TranscriptionError) as exc_info:
                transcribe(
                    audio_path=audio_path,
                    _whisper_transcribe=mock_transcribe,
                )

            assert "Transcription failed" in str(exc_info.value)


class TestParagraphExtraction:
    """Tests for paragraph extraction from Whisper output."""

    def test_extract_paragraphs_from_segments(self) -> None:
        """Paragraphs should be extracted from segments with pauses."""
        result = {
            "text": "Hello world. This is a test.",
            "segments": [
                {"text": "Hello world.", "start": 0.0, "end": 1.0},
                {"text": "This is", "start": 1.1, "end": 1.5},
                {"text": "a test.", "start": 1.6, "end": 2.0},
                # Long pause
                {"text": "New paragraph.", "start": 5.0, "end": 6.0},
            ],
        }

        paragraphs = _extract_paragraphs(result)

        assert len(paragraphs) == 2
        assert "Hello world" in paragraphs[0]
        assert "New paragraph" in paragraphs[1]

    def test_extract_paragraphs_empty_segments(self) -> None:
        """Empty segments should use full text."""
        result = {
            "text": "Just the text",
            "segments": [],
        }

        paragraphs = _extract_paragraphs(result)

        assert paragraphs == ["Just the text"]

    def test_extract_paragraphs_no_segments_key(self) -> None:
        """Missing segments key should use full text."""
        result = {
            "text": "Fallback text",
        }

        paragraphs = _extract_paragraphs(result)

        assert paragraphs == ["Fallback text"]
