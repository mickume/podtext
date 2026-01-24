"""Tests for media downloader.

Feature: podtext
Property 5: Media Storage Location
Property 6: Temporary File Cleanup
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path
import respx
from httpx import Response

from podtext.downloader import (
    download_media,
    cleanup_media,
    DownloadError,
    _get_filename_from_url,
)


class TestFilenameExtraction:
    """Tests for filename extraction from URLs."""

    def test_extract_mp3_filename(self):
        """Test extracting .mp3 filename."""
        url = "https://example.com/podcasts/episode-1.mp3"
        assert _get_filename_from_url(url) == "episode-1.mp3"

    def test_extract_with_query_params(self):
        """Test extracting filename with query parameters."""
        url = "https://example.com/episode.mp3?token=abc123"
        assert _get_filename_from_url(url) == "episode.mp3"

    def test_no_path_returns_default(self):
        """Test that no path returns default filename."""
        url = "https://example.com/"
        assert _get_filename_from_url(url) == "episode.mp3"


class TestDownloadBasics:
    """Basic download functionality tests."""

    @respx.mock
    def test_download_creates_file(self, temp_dir):
        """Test that download creates a file."""
        url = "https://example.com/episode.mp3"
        content = b"audio content"
        respx.get(url).mock(return_value=Response(200, content=content))

        result = download_media(url, temp_dir)

        assert result.exists()
        assert result.read_bytes() == content

    @respx.mock
    def test_download_creates_directory(self, temp_dir):
        """Test that download creates destination directory if needed."""
        url = "https://example.com/episode.mp3"
        dest = temp_dir / "subdir" / "deep"
        respx.get(url).mock(return_value=Response(200, content=b"audio"))

        result = download_media(url, dest)

        assert dest.exists()
        assert result.parent == dest

    @respx.mock
    def test_download_handles_duplicate_filenames(self, temp_dir):
        """Test that duplicate filenames are handled."""
        url = "https://example.com/episode.mp3"
        respx.get(url).mock(return_value=Response(200, content=b"audio"))

        # Download first file
        result1 = download_media(url, temp_dir)
        assert result1.name == "episode.mp3"

        # Download second file with same name
        result2 = download_media(url, temp_dir)
        assert result2.name == "episode_1.mp3"

    @respx.mock
    def test_download_handles_http_error(self, temp_dir):
        """Test that HTTP errors are handled."""
        url = "https://example.com/episode.mp3"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(DownloadError, match="status 404"):
            download_media(url, temp_dir)

    @respx.mock
    def test_download_follows_redirects(self, temp_dir):
        """Test that redirects are followed."""
        url = "https://example.com/redirect"
        final_url = "https://cdn.example.com/episode.mp3"

        respx.get(url).mock(
            return_value=Response(302, headers={"Location": final_url})
        )
        respx.get(final_url).mock(return_value=Response(200, content=b"audio"))

        result = download_media(url, temp_dir)
        assert result.exists()


class TestCleanup:
    """Tests for file cleanup."""

    def test_cleanup_deletes_file(self, temp_dir):
        """Test that cleanup deletes the file."""
        file_path = temp_dir / "test.mp3"
        file_path.write_bytes(b"audio")
        assert file_path.exists()

        cleanup_media(file_path)

        assert not file_path.exists()

    def test_cleanup_nonexistent_file(self, temp_dir):
        """Test that cleanup handles nonexistent files gracefully."""
        file_path = temp_dir / "nonexistent.mp3"
        # Should not raise
        cleanup_media(file_path)


class TestProperty5MediaStorageLocation:
    """Property 5: Media Storage Location.

    For any configuration with media_dir set to path P,
    downloaded media files SHALL be stored within path P.

    Validates: Requirements 3.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        subdir=st.text(
            min_size=1, max_size=20,
            alphabet=st.characters(whitelist_categories=("L", "N"), min_codepoint=ord("a"), max_codepoint=ord("z"))
        ),
    )
    @respx.mock
    def test_files_stored_in_configured_directory(self, temp_dir, subdir):
        """Downloaded files are stored in the configured media directory."""
        url = "https://example.com/episode.mp3"
        respx.get(url).mock(return_value=Response(200, content=b"audio"))

        media_dir = temp_dir / subdir
        result = download_media(url, media_dir)

        # File should be within the configured directory
        assert result.parent == media_dir
        assert str(result).startswith(str(media_dir))


class TestProperty6TemporaryFileCleanup:
    """Property 6: Temporary File Cleanup.

    For any transcription operation with temp_storage=true,
    after completion the media file SHALL not exist on disk.

    Validates: Requirements 3.3
    """

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        content=st.binary(min_size=1, max_size=1000),
    )
    def test_cleanup_removes_file(self, temp_dir, content):
        """Cleanup operation removes the media file."""
        file_path = temp_dir / "test_episode.mp3"
        file_path.write_bytes(content)

        assert file_path.exists()
        cleanup_media(file_path)
        assert not file_path.exists()

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(num_files=st.integers(min_value=1, max_value=5))
    def test_cleanup_only_removes_specified_file(self, temp_dir, num_files):
        """Cleanup only removes the specified file, not others."""
        files = []
        for i in range(num_files):
            f = temp_dir / f"episode_{i}.mp3"
            f.write_bytes(b"audio")
            files.append(f)

        # Remove first file
        cleanup_media(files[0])

        # First file should be gone
        assert not files[0].exists()

        # Other files should still exist
        for f in files[1:]:
            assert f.exists()
