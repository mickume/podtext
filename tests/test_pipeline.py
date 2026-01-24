"""Tests for transcription pipeline.

Feature: podtext
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

from podtext.pipeline import (
    transcribe_episode,
    get_episode_by_index,
    TranscriptionPipelineError,
)
from podtext.config import Config
from podtext.models import EpisodeInfo, TranscriptionResult, AnalysisResult


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock configuration."""
    return Config(
        anthropic_key="test-key",
        media_dir=temp_dir / "media",
        output_dir=temp_dir / "output",
        temp_storage=False,
        whisper_model="base",
    )


@pytest.fixture
def mock_episode():
    """Create a mock episode."""
    return EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/episode.mp3",
    )


@pytest.fixture
def mock_transcription():
    """Create a mock transcription result."""
    return TranscriptionResult(
        text="This is the transcript.",
        paragraphs=["This is the transcript."],
        language="en",
    )


@pytest.fixture
def mock_analysis():
    """Create a mock analysis result."""
    return AnalysisResult(
        summary="Summary of the episode.",
        topics=["Topic 1"],
        keywords=["keyword1"],
    )


class TestGetEpisodeByIndex:
    """Tests for getting episode by index."""

    @patch("podtext.pipeline.parse_feed")
    def test_finds_episode(self, mock_parse_feed, mock_episode):
        """Successfully finds episode by index."""
        mock_parse_feed.return_value = [mock_episode]

        result = get_episode_by_index("https://example.com/feed.xml", 1)

        assert result == mock_episode

    @patch("podtext.pipeline.parse_feed")
    def test_episode_not_found(self, mock_parse_feed):
        """Raises error when episode not found."""
        mock_parse_feed.return_value = []

        with pytest.raises(TranscriptionPipelineError, match="not found"):
            get_episode_by_index("https://example.com/feed.xml", 1)


class TestTranscribeEpisode:
    """Tests for episode transcription pipeline."""

    @patch("podtext.pipeline.parse_feed")
    @patch("podtext.pipeline.download_media")
    @patch("podtext.pipeline.transcribe")
    @patch("podtext.pipeline.detect_advertisements")
    @patch("podtext.pipeline.analyze_content")
    @patch("podtext.pipeline.generate_markdown")
    def test_successful_transcription(
        self,
        mock_generate,
        mock_analyze,
        mock_detect_ads,
        mock_transcribe,
        mock_download,
        mock_parse_feed,
        mock_config,
        mock_episode,
        mock_transcription,
        mock_analysis,
        temp_dir,
    ):
        """Successfully transcribes an episode."""
        mock_parse_feed.return_value = [mock_episode]
        mock_download.return_value = temp_dir / "episode.mp3"
        mock_transcribe.return_value = mock_transcription
        mock_detect_ads.return_value = []
        mock_analyze.return_value = mock_analysis
        mock_generate.return_value = temp_dir / "output.md"

        result = transcribe_episode(
            feed_url="https://example.com/feed.xml",
            index=1,
            config=mock_config,
        )

        assert mock_parse_feed.called
        assert mock_download.called
        assert mock_transcribe.called
        assert mock_analyze.called
        assert mock_generate.called

    @patch("podtext.pipeline.parse_feed")
    def test_feed_parse_error(self, mock_parse_feed, mock_config):
        """Handles feed parse error."""
        from podtext.rss import RSSParseError
        mock_parse_feed.side_effect = RSSParseError("Feed error")

        with pytest.raises(TranscriptionPipelineError, match="Failed to parse feed"):
            transcribe_episode(
                feed_url="https://example.com/feed.xml",
                index=1,
                config=mock_config,
            )

    @patch("podtext.pipeline.parse_feed")
    @patch("podtext.pipeline.download_media")
    def test_download_error(self, mock_download, mock_parse_feed, mock_config, mock_episode):
        """Handles download error."""
        from podtext.downloader import DownloadError
        mock_parse_feed.return_value = [mock_episode]
        mock_download.side_effect = DownloadError("Download failed")

        with pytest.raises(TranscriptionPipelineError, match="Failed to download"):
            transcribe_episode(
                feed_url="https://example.com/feed.xml",
                index=1,
                config=mock_config,
            )

    @patch("podtext.pipeline.parse_feed")
    @patch("podtext.pipeline.download_media")
    @patch("podtext.pipeline.transcribe")
    @patch("podtext.pipeline.cleanup_media")
    def test_temp_storage_cleanup(
        self,
        mock_cleanup,
        mock_transcribe,
        mock_download,
        mock_parse_feed,
        temp_dir,
        mock_episode,
        mock_transcription,
    ):
        """Cleans up media with temp_storage enabled."""
        config = Config(
            anthropic_key="",
            media_dir=temp_dir / "media",
            output_dir=temp_dir / "output",
            temp_storage=True,  # Enable temp storage
            whisper_model="base",
        )

        mock_parse_feed.return_value = [mock_episode]
        mock_download.return_value = temp_dir / "episode.mp3"
        mock_transcribe.return_value = mock_transcription

        # Create a fake file to track
        media_file = temp_dir / "episode.mp3"
        media_file.write_bytes(b"audio")

        with patch("podtext.pipeline.generate_markdown") as mock_generate:
            mock_generate.return_value = temp_dir / "output.md"

            transcribe_episode(
                feed_url="https://example.com/feed.xml",
                index=1,
                config=config,
            )

        # Cleanup should have been called
        mock_cleanup.assert_called_once()
