"""Tests for CLI interface.

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from hypothesis import given, settings, strategies as st

from podtext.cli import main
from podtext.itunes import format_search_results
from podtext.models import EpisodeInfo, PodcastSearchResult
from podtext.rss import format_episodes


# Reuse strategies from other tests
title_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
)
url_strategy = st.text(
    min_size=10,
    max_size=100,
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789/:.-_",
)


class TestSearchResultDisplayCompleteness:
    """
    Property 2: Search Result Display Completeness

    For any list of PodcastSearchResult objects, the formatted display output
    SHALL contain both the title and feed_url for each result.

    Validates: Requirements 1.2
    """

    @settings(max_examples=100)
    @given(
        st.lists(
            st.fixed_dictionaries({
                "title": title_strategy,
                "feed_url": url_strategy,
            }),
            min_size=1,
            max_size=20,
        )
    )
    def test_formatted_output_contains_title_and_url(self, items: list[dict]) -> None:
        """Property 2: Formatted output contains title and feed_url for each result."""
        results = [
            PodcastSearchResult(title=item["title"], feed_url=item["feed_url"])
            for item in items
        ]

        output = format_search_results(results)

        for result in results:
            assert result.title in output, (
                f"Title '{result.title}' should be in output"
            )
            assert result.feed_url in output, (
                f"Feed URL '{result.feed_url}' should be in output"
            )


class TestEpisodeDisplayCompleteness:
    """
    Property 3: Episode Display Completeness

    For any list of EpisodeInfo objects, the formatted display output
    SHALL contain the title, publication date, and index number for each episode.

    Validates: Requirements 2.2
    """

    @settings(max_examples=100)
    @given(
        st.lists(
            st.fixed_dictionaries({
                "index": st.integers(min_value=1, max_value=1000),
                "title": title_strategy,
            }),
            min_size=1,
            max_size=20,
            unique_by=lambda x: x["index"],
        )
    )
    def test_formatted_output_contains_index_title_date(self, items: list[dict]) -> None:
        """Property 3: Formatted output contains index, title, and date for each episode."""
        episodes = [
            EpisodeInfo(
                index=item["index"],
                title=item["title"],
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/audio.mp3",
            )
            for item in items
        ]

        output = format_episodes(episodes)

        for episode in episodes:
            assert f"{episode.index}." in output, (
                f"Index {episode.index} should be in output"
            )
            assert episode.title in output, (
                f"Title '{episode.title}' should be in output"
            )
            date_str = episode.pub_date.strftime("%Y-%m-%d")
            assert date_str in output, (
                f"Date '{date_str}' should be in output"
            )


class TestCLICommands:
    """Tests for CLI command execution."""

    @patch("podtext.cli.search_podcasts")
    def test_search_command(self, mock_search: MagicMock) -> None:
        """Search command should call search_podcasts and display results."""
        mock_search.return_value = [
            PodcastSearchResult(title="Test Podcast", feed_url="https://example.com/feed.xml")
        ]

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test", "query"])

        assert result.exit_code == 0
        assert "Test Podcast" in result.output
        assert "https://example.com/feed.xml" in result.output

    @patch("podtext.cli.search_podcasts")
    def test_search_command_with_limit(self, mock_search: MagicMock) -> None:
        """Search command should respect --limit option."""
        mock_search.return_value = []

        runner = CliRunner()
        result = runner.invoke(main, ["search", "--limit", "5", "test"])

        # Verify limit was passed
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args
        assert call_kwargs[1]["limit"] == 5

    @patch("podtext.cli.parse_feed")
    def test_episodes_command(self, mock_parse: MagicMock) -> None:
        """Episodes command should call parse_feed and display results."""
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Episode 1",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            )
        ]

        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 0
        assert "Episode 1" in result.output
        assert "2024-01-15" in result.output

    @patch("podtext.cli.parse_feed")
    def test_episodes_command_with_limit(self, mock_parse: MagicMock) -> None:
        """Episodes command should respect --limit option."""
        mock_parse.return_value = []

        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "--limit", "5", "https://example.com/feed.xml"])

        mock_parse.assert_called_once()
        call_kwargs = mock_parse.call_args
        assert call_kwargs[1]["limit"] == 5

    @patch("podtext.cli.search_podcasts")
    def test_search_error_handling(self, mock_search: MagicMock) -> None:
        """Search command should handle errors gracefully."""
        from podtext.itunes import ITunesAPIError
        mock_search.side_effect = ITunesAPIError("API Error")

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("podtext.cli.parse_feed")
    def test_episodes_error_handling(self, mock_parse: MagicMock) -> None:
        """Episodes command should handle errors gracefully."""
        from podtext.rss import RSSParseError
        mock_parse.side_effect = RSSParseError("Feed Error")

        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestCLIHelp:
    """Tests for CLI help text."""

    def test_main_help(self) -> None:
        """Main command should show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Podtext" in result.output
        assert "search" in result.output
        assert "episodes" in result.output
        assert "transcribe" in result.output

    def test_search_help(self) -> None:
        """Search command should show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])

        assert result.exit_code == 0
        assert "keywords" in result.output.lower()
        assert "--limit" in result.output

    def test_episodes_help(self) -> None:
        """Episodes command should show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "--help"])

        assert result.exit_code == 0
        assert "feed" in result.output.lower()
        assert "--limit" in result.output

    def test_transcribe_help(self) -> None:
        """Transcribe command should show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["transcribe", "--help"])

        assert result.exit_code == 0
        assert "--skip-language-check" in result.output
        assert "--output" in result.output


class TestCLIVersion:
    """Tests for CLI version."""

    def test_version_option(self) -> None:
        """Version option should display version."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
