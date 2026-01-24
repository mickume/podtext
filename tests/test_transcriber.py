"""Tests for transcriber service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx
import respx

from podtext.config.manager import Config
from podtext.models.transcript import Transcript
from podtext.services.transcriber import TranscriberService, TranscriptionError


class TestTranscriberService:
    """Tests for TranscriberService."""

    def test_init_sets_whisper_model(self):
        """Test that init sets correct whisper model path."""
        config = Config(whisper_model="small")
        service = TranscriberService(config)

        assert service.whisper_model == "mlx-community/whisper-small-mlx"

    @respx.mock
    def test_download_media_success(self, tmp_path):
        """Test successful media download."""
        audio_data = b"fake audio data"
        respx.get("https://example.com/episode.mp3").mock(
            return_value=httpx.Response(200, content=audio_data)
        )

        config = Config()
        service = TranscriberService(config)

        output_path = tmp_path / "test.mp3"
        result = service.download_media("https://example.com/episode.mp3", output_path)

        assert result == output_path
        assert result.exists()
        assert result.read_bytes() == audio_data

    @respx.mock
    def test_download_media_to_temp(self):
        """Test download to temp file when no path specified."""
        audio_data = b"fake audio data"
        respx.get("https://example.com/episode.mp3").mock(
            return_value=httpx.Response(200, content=audio_data)
        )

        config = Config()
        service = TranscriberService(config)

        result = service.download_media("https://example.com/episode.mp3")

        assert result.exists()
        assert result.suffix == ".mp3"

        # Cleanup
        result.unlink()

    @respx.mock
    def test_download_media_http_error(self):
        """Test handling of HTTP errors during download."""
        respx.get("https://example.com/episode.mp3").mock(
            return_value=httpx.Response(404)
        )

        config = Config()
        service = TranscriberService(config)

        with pytest.raises(TranscriptionError) as exc_info:
            service.download_media("https://example.com/episode.mp3")

        assert "404" in str(exc_info.value)

    @respx.mock
    def test_download_media_timeout(self):
        """Test handling of timeout during download."""
        respx.get("https://example.com/episode.mp3").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        config = Config()
        service = TranscriberService(config)

        with pytest.raises(TranscriptionError) as exc_info:
            service.download_media("https://example.com/episode.mp3")

        assert "timed out" in str(exc_info.value).lower()

    def test_transcribe_file_not_found(self, tmp_path):
        """Test error when media file doesn't exist."""
        config = Config()
        service = TranscriberService(config)

        with pytest.raises(TranscriptionError) as exc_info:
            service.transcribe(tmp_path / "nonexistent.mp3")

        assert "not found" in str(exc_info.value).lower()

    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_success(self, mock_whisper, tmp_path):
        """Test successful transcription."""
        # Create test file
        media_file = tmp_path / "test.mp3"
        media_file.write_bytes(b"fake audio")

        # Mock whisper result
        mock_whisper.transcribe.return_value = {
            "text": "Hello world. This is a test.",
            "language": "en",
            "segments": [
                {"text": " Hello world.", "start": 0.0, "end": 2.0},
                {"text": " This is a test.", "start": 2.5, "end": 5.0},
            ],
        }

        config = Config()
        service = TranscriberService(config)

        result = service.transcribe(media_file)

        assert isinstance(result, Transcript)
        assert result.text == "Hello world. This is a test."
        assert result.language == "en"
        assert len(result.segments) == 2

    @patch("podtext.services.transcriber.mlx_whisper")
    def test_transcribe_creates_paragraphs(self, mock_whisper, tmp_path):
        """Test paragraph creation from segments."""
        media_file = tmp_path / "test.mp3"
        media_file.write_bytes(b"fake audio")

        # Segments with a gap > 2 seconds should create paragraph break
        mock_whisper.transcribe.return_value = {
            "text": "First part. Second part.",
            "language": "en",
            "segments": [
                {"text": " First part.", "start": 0.0, "end": 2.0},
                {"text": " Second part.", "start": 5.0, "end": 7.0},  # 3 second gap
            ],
        }

        config = Config()
        service = TranscriberService(config)

        result = service.transcribe(media_file)

        assert len(result.paragraphs) == 2
        assert result.paragraphs[0] == "First part."
        assert result.paragraphs[1] == "Second part."

    def test_cleanup_media_when_enabled(self, tmp_path):
        """Test media cleanup when enabled."""
        media_file = tmp_path / "test.mp3"
        media_file.write_bytes(b"data")

        config = Config(cleanup_media=True)
        service = TranscriberService(config)

        service.cleanup_media(media_file)

        assert not media_file.exists()

    def test_cleanup_media_when_disabled(self, tmp_path):
        """Test media not cleaned up when disabled."""
        media_file = tmp_path / "test.mp3"
        media_file.write_bytes(b"data")

        config = Config(cleanup_media=False)
        service = TranscriberService(config)

        service.cleanup_media(media_file)

        assert media_file.exists()

    def test_get_extension_from_url(self):
        """Test file extension extraction from URL."""
        config = Config()
        service = TranscriberService(config)

        assert service._get_extension("https://example.com/ep.mp3") == ".mp3"
        assert service._get_extension("https://example.com/ep.m4a?token=abc") == ".m4a"
        assert service._get_extension("https://example.com/ep.mp4") == ".mp4"
        assert service._get_extension("https://example.com/audio") == ".mp3"  # default
