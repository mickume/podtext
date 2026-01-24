"""Tests for download service."""

import tempfile
from datetime import UTC
from pathlib import Path

import pytest
import respx
from httpx import Response

from podtext.core.errors import DownloadError
from podtext.core.models import Episode
from podtext.services.download import DownloadService


class TestDownloadService:
    """Tests for DownloadService."""

    def test_init_creates_directory(self) -> None:
        """Test that init creates the download directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            assert not download_dir.exists()

            DownloadService(download_dir)
            assert download_dir.exists()

    @respx.mock
    def test_download_success(self, sample_episode: Episode) -> None:
        """Test successful media download."""
        respx.get(sample_episode.media_url).mock(
            return_value=Response(200, content=b"fake audio data")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            path = service.download(sample_episode)

            assert path.exists()
            assert path.read_bytes() == b"fake audio data"

    @respx.mock
    def test_download_failure(self, sample_episode: Episode) -> None:
        """Test download failure handling."""
        respx.get(sample_episode.media_url).mock(
            return_value=Response(404)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            with pytest.raises(DownloadError) as exc_info:
                service.download(sample_episode)

            assert "Failed to download media" in str(exc_info.value)

    def test_download_no_media_url(self) -> None:
        """Test download with missing media URL."""
        from datetime import datetime

        episode = Episode(
            index=1,
            title="No Media",
            published=datetime.now(UTC),
            media_url="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            with pytest.raises(DownloadError) as exc_info:
                service.download(episode)

            assert "No media URL" in str(exc_info.value)

    def test_cleanup_existing_file(self) -> None:
        """Test cleanup of existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            test_file = Path(tmpdir) / "test.mp3"
            test_file.write_text("test")

            assert test_file.exists()
            service.cleanup(test_file)
            assert not test_file.exists()

    def test_cleanup_nonexistent_file(self) -> None:
        """Test cleanup of non-existent file (should not raise)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            test_file = Path(tmpdir) / "nonexistent.mp3"

            # Should not raise
            service.cleanup(test_file)

    def test_is_video_true(self) -> None:
        """Test video file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))

            assert service._is_video(Path("test.mp4"))
            assert service._is_video(Path("test.mkv"))
            assert service._is_video(Path("test.webm"))

    def test_is_video_false(self) -> None:
        """Test non-video file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))

            assert not service._is_video(Path("test.mp3"))
            assert not service._is_video(Path("test.m4a"))
            assert not service._is_video(Path("test.wav"))


class TestFilenameExtraction:
    """Tests for filename extraction from URLs."""

    def test_simple_url(self) -> None:
        """Test extracting filename from simple URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            filename = service._get_filename_from_url(
                "https://example.com/podcast/episode.mp3"
            )
            assert filename == "episode.mp3"

    def test_url_with_query_params(self) -> None:
        """Test extracting filename from URL with query params."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            filename = service._get_filename_from_url(
                "https://example.com/episode.mp3?token=abc123"
            )
            assert filename == "episode.mp3"

    def test_url_encoded_filename(self) -> None:
        """Test extracting URL-encoded filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            filename = service._get_filename_from_url(
                "https://example.com/my%20episode.mp3"
            )
            assert filename == "my_episode.mp3" or "my episode.mp3" in filename

    def test_url_without_extension(self) -> None:
        """Test handling URL without extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DownloadService(Path(tmpdir))
            filename = service._get_filename_from_url(
                "https://example.com/episode"
            )
            # Should add an extension
            assert filename.endswith(".mp3")


# Fixture used above needs to be available
@pytest.fixture
def sample_episode() -> Episode:
    """Create a sample episode for testing."""
    from datetime import datetime

    return Episode(
        index=1,
        title="Test Episode",
        published=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        media_url="https://example.com/episode.mp3",
        duration=3600,
        description="A test episode",
    )
