"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest
from click.testing import CliRunner

from podtext.cli.main import cli
from podtext.models.podcast import Episode, Podcast


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config(tmp_path):
    """Create mock config setup."""
    # Create config directory
    config_dir = tmp_path / ".podtext"
    config_dir.mkdir()

    config_content = """
[general]
output_dir = "./transcripts"

[defaults]
search_limit = 10
episode_limit = 10
"""
    (config_dir / "config.toml").write_text(config_content)

    analysis_content = """
## Summary Prompt
Generate summary.

## Topics Prompt
List topics.

## Keywords Prompt
Extract keywords.

## Advertising Detection Prompt
Find ads.
"""
    (config_dir / "ANALYSIS.md").write_text(analysis_content)

    return tmp_path


class TestSearchCommand:
    """Tests for search command."""

    @patch("podtext.cli.search.PodcastService")
    def test_search_displays_results(self, MockService, runner, mock_config):
        """Test search displays results correctly."""
        mock_service = MockService.return_value
        mock_service.search.return_value = [
            Podcast(
                title="Tech Talk",
                feed_url="https://example.com/tech.xml",
                author="Tech Media",
                genre="Technology",
            ),
            Podcast(
                title="Science Hour",
                feed_url="https://example.com/science.xml",
                author="Science Network",
            ),
        ]

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(cli, ["search", "technology"])

        assert result.exit_code == 0
        assert "Tech Talk" in result.output
        assert "Tech Media" in result.output
        assert "Science Hour" in result.output

    @patch("podtext.cli.search.PodcastService")
    def test_search_no_results(self, MockService, runner, mock_config):
        """Test search with no results."""
        mock_service = MockService.return_value
        mock_service.search.return_value = []

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(cli, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No podcasts found" in result.output

    @patch("podtext.cli.search.PodcastService")
    def test_search_with_limit(self, MockService, runner, mock_config):
        """Test search with custom limit."""
        mock_service = MockService.return_value
        mock_service.search.return_value = []

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(cli, ["search", "test", "-n", "25"])

        mock_service.search.assert_called_once_with("test", 25)


class TestEpisodesCommand:
    """Tests for episodes command."""

    @patch("podtext.cli.episodes.PodcastService")
    def test_episodes_displays_list(self, MockService, runner, mock_config):
        """Test episodes displays list correctly."""
        mock_service = MockService.return_value
        mock_service.get_episodes.return_value = [
            Episode(
                title="Episode 10",
                pub_date=datetime(2024, 3, 20),
                media_url="https://example.com/ep10.mp3",
                duration=3600,
            ),
            Episode(
                title="Episode 9",
                pub_date=datetime(2024, 3, 13),
                media_url="https://example.com/ep9.mp3",
            ),
        ]
        mock_service.get_podcast_name.return_value = "Test Podcast"

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(cli, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 0
        assert "Test Podcast" in result.output
        assert "Episode 10" in result.output
        assert "Episode 9" in result.output
        assert "2024-03-20" in result.output

    @patch("podtext.cli.episodes.PodcastService")
    def test_episodes_shows_usage_hint(self, MockService, runner, mock_config):
        """Test episodes shows transcribe usage hint."""
        mock_service = MockService.return_value
        mock_service.get_episodes.return_value = [
            Episode(
                title="Episode",
                pub_date=datetime(2024, 3, 20),
                media_url="https://example.com/ep.mp3",
            )
        ]
        mock_service.get_podcast_name.return_value = "Podcast"

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(cli, ["episodes", "https://example.com/feed.xml"])

        assert "podtext transcribe" in result.output


class TestTranscribeCommand:
    """Tests for transcribe command."""

    @patch("podtext.cli.transcribe.MarkdownWriter")
    @patch("podtext.cli.transcribe.TranscriberService")
    @patch("podtext.cli.transcribe.PodcastService")
    def test_transcribe_basic_flow(
        self, MockPodcast, MockTranscriber, MockWriter, runner, mock_config, tmp_path
    ):
        """Test basic transcribe flow."""
        from podtext.models.transcript import Transcript

        # Setup mocks
        mock_podcast = MockPodcast.return_value
        mock_podcast.get_episode_by_index.return_value = Episode(
            title="Test Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
        )
        mock_podcast.get_podcast_name.return_value = "Test Podcast"

        mock_transcriber = MockTranscriber.return_value
        mock_transcriber.download_media.return_value = tmp_path / "test.mp3"
        mock_transcriber.transcribe.return_value = Transcript(
            text="Transcript text.", language="en"
        )

        mock_writer = MockWriter.return_value
        mock_writer.write.return_value = tmp_path / "output.md"

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1", "--skip-analysis"],
            )

        assert result.exit_code == 0
        assert "Success" in result.output

    @patch("podtext.cli.transcribe.PodcastService")
    def test_transcribe_invalid_index(self, MockPodcast, runner, mock_config):
        """Test transcribe with invalid episode index."""
        from podtext.services.podcast import PodcastError

        mock_podcast = MockPodcast.return_value
        mock_podcast.get_episode_by_index.side_effect = PodcastError(
            "Episode index 99 out of range"
        )

        with runner.isolated_filesystem(temp_dir=mock_config):
            result = runner.invoke(
                cli, ["transcribe", "https://example.com/feed.xml", "99"]
            )

        assert result.exit_code != 0
        assert "out of range" in result.output


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self, runner):
        """Test main help output."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "podtext" in result.output
        assert "search" in result.output
        assert "episodes" in result.output
        assert "transcribe" in result.output

    def test_search_help(self, runner):
        """Test search help output."""
        result = runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0
        assert "TERM" in result.output
        assert "--limit" in result.output

    def test_episodes_help(self, runner):
        """Test episodes help output."""
        result = runner.invoke(cli, ["episodes", "--help"])

        assert result.exit_code == 0
        assert "FEED_URL" in result.output
        assert "--limit" in result.output

    def test_transcribe_help(self, runner):
        """Test transcribe help output."""
        result = runner.invoke(cli, ["transcribe", "--help"])

        assert result.exit_code == 0
        assert "FEED_URL" in result.output
        assert "INDEX" in result.output
        assert "--skip-language-check" in result.output
        assert "--skip-analysis" in result.output
