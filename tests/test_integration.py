"""Integration tests for Podtext.

Tests end-to-end flows with mocked external APIs.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import respx
from httpx import Response

from podtext.cli import main
from podtext.config import load_config, get_global_config_path
from podtext.itunes import ITUNES_SEARCH_URL


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestConfigCreation:
    """Tests for config file creation on first run."""

    def test_global_config_created_on_load(self, mock_home):
        """Global config is created when it doesn't exist."""
        global_path = get_global_config_path()
        assert not global_path.exists()

        # Load config should create global config
        config = load_config(create_global=True)

        assert global_path.exists()
        assert global_path.read_text()  # Has content

    def test_config_has_expected_structure(self, mock_home):
        """Created config has expected TOML structure."""
        load_config(create_global=True)

        global_path = get_global_config_path()
        content = global_path.read_text()

        assert "[api]" in content
        assert "[storage]" in content
        assert "[whisper]" in content


class TestEndToEndSearch:
    """End-to-end tests for search workflow."""

    @respx.mock
    def test_search_and_display_flow(self, runner):
        """Complete search flow from CLI to display."""
        mock_response = {
            "resultCount": 3,
            "results": [
                {"collectionName": "Python Podcast", "feedUrl": "https://python.fm/rss"},
                {"collectionName": "Code Radio", "feedUrl": "https://code.fm/rss"},
                {"collectionName": "Dev Talk", "feedUrl": "https://dev.fm/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        result = runner.invoke(main, ["search", "python", "programming"])

        assert result.exit_code == 0

        # All results should be displayed
        assert "Python Podcast" in result.output
        assert "Code Radio" in result.output
        assert "Dev Talk" in result.output

        # Feed URLs should be included
        assert "https://python.fm/rss" in result.output
        assert "https://code.fm/rss" in result.output
        assert "https://dev.fm/rss" in result.output

    @respx.mock
    def test_search_with_limit(self, runner):
        """Search respects the limit parameter."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {"collectionName": "Podcast 1", "feedUrl": "https://1.fm/rss"},
                {"collectionName": "Podcast 2", "feedUrl": "https://2.fm/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        result = runner.invoke(main, ["search", "test", "--limit", "2"])

        assert result.exit_code == 0
        assert "Podcast 1" in result.output
        assert "Podcast 2" in result.output


class TestEndToEndEpisodes:
    """End-to-end tests for episode listing workflow."""

    def test_episodes_with_valid_feed(self, runner, temp_dir):
        """Complete episode listing flow with a local RSS feed."""
        # Create a test RSS feed
        feed_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Podcast</title>
    <item>
      <title>Episode 1: Getting Started</title>
      <pubDate>Mon, 15 Jan 2024 12:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg"/>
    </item>
    <item>
      <title>Episode 2: Advanced Topics</title>
      <pubDate>Tue, 16 Jan 2024 12:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg"/>
    </item>
  </channel>
</rss>
"""
        feed_path = temp_dir / "feed.xml"
        feed_path.write_text(feed_content)

        result = runner.invoke(main, ["episodes", str(feed_path)])

        assert result.exit_code == 0

        # Episodes should be displayed (newest first)
        assert "Episode 2: Advanced Topics" in result.output
        assert "Episode 1: Getting Started" in result.output

        # Dates should be included
        assert "2024-01-16" in result.output
        assert "2024-01-15" in result.output


class TestErrorHandling:
    """Tests for error handling in various scenarios."""

    @respx.mock
    def test_search_api_failure(self, runner):
        """Search handles API failures gracefully."""
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(503))

        result = runner.invoke(main, ["search", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_episodes_invalid_feed(self, runner, temp_dir):
        """Episodes handles invalid feed gracefully."""
        feed_path = temp_dir / "invalid.xml"
        feed_path.write_text("not valid xml {{{")

        result = runner.invoke(main, ["episodes", str(feed_path)])

        # Should exit with error
        assert result.exit_code == 1

    def test_episodes_empty_feed(self, runner, temp_dir):
        """Episodes handles empty feed gracefully."""
        feed_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Podcast</title>
  </channel>
</rss>
"""
        feed_path = temp_dir / "empty.xml"
        feed_path.write_text(feed_content)

        result = runner.invoke(main, ["episodes", str(feed_path)])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestTranscribeMocked:
    """Tests for transcribe command with mocked components."""

    @patch("podtext.pipeline.transcribe_episode")
    def test_transcribe_success(self, mock_transcribe, runner, temp_dir):
        """Transcribe command succeeds with mocked pipeline."""
        mock_transcribe.return_value = temp_dir / "output.md"

        result = runner.invoke(main, [
            "transcribe",
            "https://example.com/feed.xml",
            "1"
        ])

        assert result.exit_code == 0
        assert "Transcription saved to" in result.output

    @patch("podtext.pipeline.transcribe_episode")
    def test_transcribe_with_skip_language_check(self, mock_transcribe, runner, temp_dir):
        """Transcribe respects skip-language-check flag."""
        mock_transcribe.return_value = temp_dir / "output.md"

        result = runner.invoke(main, [
            "transcribe",
            "https://example.com/feed.xml",
            "1",
            "--skip-language-check"
        ])

        assert result.exit_code == 0

        # Verify flag was passed to pipeline
        call_kwargs = mock_transcribe.call_args.kwargs
        assert call_kwargs.get("skip_language_check") is True

    @patch("podtext.pipeline.transcribe_episode")
    def test_transcribe_pipeline_error(self, mock_transcribe, runner):
        """Transcribe handles pipeline errors."""
        from podtext.pipeline import TranscriptionPipelineError
        mock_transcribe.side_effect = TranscriptionPipelineError("Something went wrong")

        result = runner.invoke(main, [
            "transcribe",
            "https://example.com/feed.xml",
            "1"
        ])

        assert result.exit_code == 1
        assert "Error" in result.output
