"""Unit tests for the media downloader.

Tests media download functionality, storage, cleanup, and error handling.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from podtext.core.config import Config, StorageConfig
from podtext.services.downloader import (
    DownloadError,
    _extract_filename_from_url,
    cleanup_media_file,
    download_media,
    download_media_to_config_dir,
    download_with_optional_cleanup,
    temporary_download,
)


class TestExtractFilenameFromUrl:
    """Tests for _extract_filename_from_url function."""

    def test_extract_simple_filename(self) -> None:
        """Test extracting filename from simple URL."""
        url = "https://example.com/podcast/episode.mp3"
        filename = _extract_filename_from_url(url)
        assert filename == "episode.mp3"

    def test_extract_filename_with_query_params(self) -> None:
        """Test extracting filename from URL with query parameters."""
        url = "https://example.com/podcast/episode.mp3?token=abc123"
        filename = _extract_filename_from_url(url)
        assert filename == "episode.mp3"

    def test_extract_filename_url_encoded(self) -> None:
        """Test extracting filename from URL-encoded path."""
        url = "https://example.com/podcast/my%20episode.mp3"
        filename = _extract_filename_from_url(url)
        assert filename == "my episode.mp3"

    def test_extract_filename_no_extension(self) -> None:
        """Test fallback when URL has no file extension."""
        url = "https://example.com/podcast/episode"
        filename = _extract_filename_from_url(url)
        # Should return hash-based fallback
        assert filename.startswith("media_")

    def test_extract_filename_empty_path(self) -> None:
        """Test fallback when URL has empty path."""
        url = "https://example.com/"
        filename = _extract_filename_from_url(url)
        assert filename.startswith("media_")

    def test_extract_filename_different_extensions(self) -> None:
        """Test extracting filenames with various extensions."""
        urls_and_expected = [
            ("https://example.com/audio.m4a", "audio.m4a"),
            ("https://example.com/video.mp4", "video.mp4"),
            ("https://example.com/audio.wav", "audio.wav"),
            ("https://example.com/audio.ogg", "audio.ogg"),
        ]
        for url, expected in urls_and_expected:
            assert _extract_filename_from_url(url) == expected


class TestDownloadMedia:
    """Tests for download_media function.

    Validates: Requirements 3.1, 3.4
    """

    @patch("podtext.services.downloader.httpx.stream")
    def test_download_successful(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test successful media download.

        Validates: Requirement 3.1
        """
        dest_path = tmp_path / "downloads" / "episode.mp3"
        test_content = b"fake audio content"

        # Setup mock response
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [test_content]
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_stream.return_value = mock_response

        result = download_media("https://example.com/episode.mp3", dest_path)

        assert result == dest_path
        assert dest_path.exists()
        assert dest_path.read_bytes() == test_content

    @patch("podtext.services.downloader.httpx.stream")
    def test_download_creates_parent_directories(
        self, mock_stream: MagicMock, tmp_path: Path
    ) -> None:
        """Test that download creates parent directories if needed."""
        dest_path = tmp_path / "deep" / "nested" / "path" / "episode.mp3"
        test_content = b"audio"

        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [test_content]
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_stream.return_value = mock_response

        result = download_media("https://example.com/episode.mp3", dest_path)

        assert result == dest_path
        assert dest_path.exists()

    @patch("podtext.services.downloader.httpx.stream")
    def test_download_chunked_content(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test downloading content in chunks."""
        dest_path = tmp_path / "episode.mp3"
        chunks = [b"chunk1", b"chunk2", b"chunk3"]

        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = chunks
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_stream.return_value = mock_response

        download_media("https://example.com/episode.mp3", dest_path)

        assert dest_path.read_bytes() == b"chunk1chunk2chunk3"


class TestDownloadMediaErrorHandling:
    """Tests for error handling in download_media.

    Validates: Requirement 3.4
    """

    @patch("podtext.services.downloader.httpx.stream")
    def test_timeout_error(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test that timeout raises DownloadError.

        Validates: Requirement 3.4
        """
        dest_path = tmp_path / "episode.mp3"
        mock_stream.side_effect = httpx.TimeoutException("Connection timed out")

        with pytest.raises(DownloadError) as exc_info:
            download_media("https://example.com/episode.mp3", dest_path)

        assert "timed out" in str(exc_info.value).lower()
        assert not dest_path.exists()

    @patch("podtext.services.downloader.httpx.stream")
    def test_http_status_error(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test that HTTP error status raises DownloadError.

        Validates: Requirement 3.4
        """
        dest_path = tmp_path / "episode.mp3"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_stream.return_value = mock_response

        with pytest.raises(DownloadError) as exc_info:
            download_media("https://example.com/episode.mp3", dest_path)

        assert "404" in str(exc_info.value)
        assert not dest_path.exists()

    @patch("podtext.services.downloader.httpx.stream")
    def test_connection_error(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test that connection error raises DownloadError.

        Validates: Requirement 3.4
        """
        dest_path = tmp_path / "episode.mp3"
        mock_stream.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(DownloadError) as exc_info:
            download_media("https://example.com/episode.mp3", dest_path)

        assert "Failed to download" in str(exc_info.value)
        assert not dest_path.exists()

    @patch("podtext.services.downloader.httpx.stream")
    def test_request_error(self, mock_stream: MagicMock, tmp_path: Path) -> None:
        """Test that generic request error raises DownloadError.

        Validates: Requirement 3.4
        """
        dest_path = tmp_path / "episode.mp3"
        mock_stream.side_effect = httpx.RequestError("Network error")

        with pytest.raises(DownloadError) as exc_info:
            download_media("https://example.com/episode.mp3", dest_path)

        assert "Failed to download" in str(exc_info.value)

    @patch("podtext.services.downloader.httpx.stream")
    def test_partial_download_cleanup_on_error(
        self, mock_stream: MagicMock, tmp_path: Path
    ) -> None:
        """Test that partial downloads are cleaned up on error."""
        dest_path = tmp_path / "episode.mp3"

        # Create a partial file to simulate interrupted download
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(b"partial content")

        mock_stream.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(DownloadError):
            download_media("https://example.com/episode.mp3", dest_path)

        # File should be cleaned up
        assert not dest_path.exists()


class TestDownloadMediaToConfigDir:
    """Tests for download_media_to_config_dir function.

    Validates: Requirements 3.1, 3.2
    """

    @patch("podtext.services.downloader.download_media")
    def test_download_to_config_dir(self, mock_download: MagicMock, tmp_path: Path) -> None:
        """Test downloading to configured media directory.

        Validates: Requirement 3.2
        """
        media_dir = tmp_path / "media"
        config = Config(storage=StorageConfig(media_dir=str(media_dir)))
        expected_path = media_dir / "episode.mp3"
        mock_download.return_value = expected_path

        result = download_media_to_config_dir(
            "https://example.com/episode.mp3",
            config,
            filename="episode.mp3",
        )

        assert result == expected_path
        mock_download.assert_called_once_with(
            "https://example.com/episode.mp3",
            expected_path,
        )

    @patch("podtext.services.downloader.download_media")
    def test_download_extracts_filename_from_url(
        self, mock_download: MagicMock, tmp_path: Path
    ) -> None:
        """Test that filename is extracted from URL when not provided."""
        media_dir = tmp_path / "media"
        config = Config(storage=StorageConfig(media_dir=str(media_dir)))
        expected_path = media_dir / "podcast_episode.mp3"
        mock_download.return_value = expected_path

        download_media_to_config_dir(
            "https://example.com/path/podcast_episode.mp3",
            config,
        )

        call_args = mock_download.call_args
        assert call_args[0][1].name == "podcast_episode.mp3"


class TestCleanupMediaFile:
    """Tests for cleanup_media_file function.

    Validates: Requirement 3.3
    """

    def test_cleanup_existing_file(self, tmp_path: Path) -> None:
        """Test cleaning up an existing file.

        Validates: Requirement 3.3
        """
        file_path = tmp_path / "episode.mp3"
        file_path.write_bytes(b"audio content")

        result = cleanup_media_file(file_path)

        assert result is True
        assert not file_path.exists()

    def test_cleanup_nonexistent_file(self, tmp_path: Path) -> None:
        """Test cleaning up a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.mp3"

        result = cleanup_media_file(file_path)

        assert result is False

    def test_cleanup_handles_permission_error(self, tmp_path: Path) -> None:
        """Test that cleanup handles permission errors gracefully."""
        file_path = tmp_path / "episode.mp3"
        file_path.write_bytes(b"content")

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            result = cleanup_media_file(file_path)

        # Should return False on error, not raise
        assert result is False


class TestTemporaryDownload:
    """Tests for temporary_download context manager.

    Validates: Requirement 3.3
    """

    @patch("podtext.services.downloader.download_media_to_config_dir")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_temporary_download_cleanup(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that temporary download cleans up file after use.

        Validates: Requirement 3.3
        """
        file_path = tmp_path / "episode.mp3"
        mock_download.return_value = file_path
        config = Config()

        with temporary_download("https://example.com/ep.mp3", config) as path:
            assert path == file_path

        mock_cleanup.assert_called_once_with(file_path)

    @patch("podtext.services.downloader.download_media_to_config_dir")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_temporary_download_cleanup_on_exception(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that cleanup happens even when exception occurs."""
        file_path = tmp_path / "episode.mp3"
        mock_download.return_value = file_path
        config = Config()

        with pytest.raises(ValueError):
            with temporary_download("https://example.com/ep.mp3", config):
                raise ValueError("Test error")

        mock_cleanup.assert_called_once_with(file_path)


class TestDownloadWithOptionalCleanup:
    """Tests for download_with_optional_cleanup context manager.

    Validates: Requirements 3.2, 3.3
    """

    @patch("podtext.services.downloader.download_media_to_config_dir")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_cleanup_when_temp_storage_enabled(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup when temp_storage is True.

        Validates: Requirement 3.3
        """
        file_path = tmp_path / "episode.mp3"
        mock_download.return_value = file_path
        config = Config(storage=StorageConfig(temp_storage=True))

        with download_with_optional_cleanup("https://example.com/ep.mp3", config) as path:
            assert path == file_path

        mock_cleanup.assert_called_once_with(file_path)

    @patch("podtext.services.downloader.download_media_to_config_dir")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_no_cleanup_when_temp_storage_disabled(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test no cleanup when temp_storage is False.

        Validates: Requirement 3.2
        """
        file_path = tmp_path / "episode.mp3"
        mock_download.return_value = file_path
        config = Config(storage=StorageConfig(temp_storage=False))

        with download_with_optional_cleanup("https://example.com/ep.mp3", config) as path:
            assert path == file_path

        mock_cleanup.assert_not_called()

    @patch("podtext.services.downloader.download_media_to_config_dir")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_cleanup_on_exception_when_temp_storage_enabled(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup happens on exception when temp_storage is True."""
        file_path = tmp_path / "episode.mp3"
        mock_download.return_value = file_path
        config = Config(storage=StorageConfig(temp_storage=True))

        with pytest.raises(ValueError):
            with download_with_optional_cleanup("https://example.com/ep.mp3", config):
                raise ValueError("Test error")

        mock_cleanup.assert_called_once_with(file_path)
