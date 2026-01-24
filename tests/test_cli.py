"""Tests for CLI interface.

Feature: podtext
Property 2: Search Result Display Completeness
Property 3: Episode Display Completeness
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from click.testing import CliRunner
import respx
from httpx import Response

from podtext.cli import (
    main,
    format_search_results,
    format_episode_list,
)
from podtext.models import PodcastSearchResult, EpisodeInfo
from podtext.itunes import ITUNES_SEARCH_URL


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestSearchCommand:
    """Tests for search command."""

    @respx.mock
    def test_search_displays_results(self, runner):
        """Search displays podcast results."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {"collectionName": "Podcast One", "feedUrl": "https://feed1.com/rss"},
                {"collectionName": "Podcast Two", "feedUrl": "https://feed2.com/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        result = runner.invoke(main, ["search", "test"])

        assert result.exit_code == 0
        assert "Podcast One" in result.output
        assert "Podcast Two" in result.output

    @respx.mock
    def test_search_no_results(self, runner):
        """Search handles no results."""
        mock_response = {"resultCount": 0, "results": []}
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        result = runner.invoke(main, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No podcasts found" in result.output

    @respx.mock
    def test_search_with_limit(self, runner):
        """Search respects limit option."""
        mock_response = {
            "resultCount": 1,
            "results": [
                {"collectionName": "Podcast", "feedUrl": "https://feed.com/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        result = runner.invoke(main, ["search", "test", "--limit", "5"])

        assert result.exit_code == 0

    @respx.mock
    def test_search_api_error(self, runner):
        """Search handles API errors."""
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(500))

        result = runner.invoke(main, ["search", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestEpisodesCommand:
    """Tests for episodes command."""

    def test_episodes_no_args(self, runner):
        """Episodes requires feed URL."""
        result = runner.invoke(main, ["episodes"])
        assert result.exit_code != 0


class TestFormatSearchResults:
    """Tests for search result formatting."""

    def test_format_single_result(self):
        """Format single search result."""
        results = [PodcastSearchResult(title="Test Podcast", feed_url="https://example.com/rss")]
        output = format_search_results(results)

        assert "1. Test Podcast" in output
        assert "https://example.com/rss" in output

    def test_format_multiple_results(self):
        """Format multiple search results."""
        results = [
            PodcastSearchResult(title="Podcast One", feed_url="https://one.com/rss"),
            PodcastSearchResult(title="Podcast Two", feed_url="https://two.com/rss"),
        ]
        output = format_search_results(results)

        assert "1. Podcast One" in output
        assert "2. Podcast Two" in output


class TestFormatEpisodeList:
    """Tests for episode list formatting."""

    def test_format_single_episode(self):
        """Format single episode."""
        episodes = [
            EpisodeInfo(
                index=1,
                title="Episode Title",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep.mp3",
            )
        ]
        output = format_episode_list(episodes)

        assert "1." in output
        assert "2024-01-15" in output
        assert "Episode Title" in output

    def test_format_multiple_episodes(self):
        """Format multiple episodes."""
        episodes = [
            EpisodeInfo(index=1, title="Episode 1", pub_date=datetime(2024, 1, 15), media_url="https://example.com/1.mp3"),
            EpisodeInfo(index=2, title="Episode 2", pub_date=datetime(2024, 1, 14), media_url="https://example.com/2.mp3"),
        ]
        output = format_episode_list(episodes)

        assert "1." in output
        assert "2." in output
        assert "Episode 1" in output
        assert "Episode 2" in output


class TestProperty2SearchResultDisplayCompleteness:
    """Property 2: Search Result Display Completeness.

    For any list of PodcastSearchResult objects, the formatted display output
    SHALL contain both the title and feed_url for each result.

    Validates: Requirements 1.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
        feed_url=st.text(min_size=10, max_size=50, alphabet=st.characters(
            whitelist_categories=("L", "N"),
            whitelist_characters="://.-_"
        )).map(lambda x: f"https://{x}"),
    )
    def test_output_contains_title_and_url(self, title, feed_url):
        """Output contains both title and feed_url for each result."""
        results = [PodcastSearchResult(title=title, feed_url=feed_url)]
        output = format_search_results(results)

        assert title in output
        assert feed_url in output

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(num_results=st.integers(min_value=1, max_value=10))
    def test_all_results_in_output(self, num_results):
        """All results appear in output."""
        results = [
            PodcastSearchResult(
                title=f"Podcast_{i}",
                feed_url=f"https://feed{i}.com/rss"
            )
            for i in range(num_results)
        ]
        output = format_search_results(results)

        for result in results:
            assert result.title in output
            assert result.feed_url in output


class TestProperty3EpisodeDisplayCompleteness:
    """Property 3: Episode Display Completeness.

    For any list of EpisodeInfo objects, the formatted display output
    SHALL contain the title, publication date, and index number for each episode.

    Validates: Requirements 2.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
        index=st.integers(min_value=1, max_value=100),
        day=st.integers(min_value=1, max_value=28),
        month=st.integers(min_value=1, max_value=12),
        year=st.integers(min_value=2000, max_value=2030),
    )
    def test_output_contains_title_date_index(self, title, index, day, month, year):
        """Output contains title, date, and index for each episode."""
        pub_date = datetime(year, month, day)
        episodes = [
            EpisodeInfo(
                index=index,
                title=title,
                pub_date=pub_date,
                media_url="https://example.com/ep.mp3",
            )
        ]
        output = format_episode_list(episodes)

        # Title should be in output
        assert title in output

        # Date should be in output (YYYY-MM-DD format)
        date_str = pub_date.strftime("%Y-%m-%d")
        assert date_str in output

        # Index should be in output
        assert f"{index}." in output

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(num_episodes=st.integers(min_value=1, max_value=10))
    def test_all_episodes_in_output(self, num_episodes):
        """All episodes appear in output."""
        episodes = [
            EpisodeInfo(
                index=i,
                title=f"Episode_{i}",
                pub_date=datetime(2024, 1, i if i <= 28 else 28),
                media_url=f"https://example.com/{i}.mp3",
            )
            for i in range(1, num_episodes + 1)
        ]
        output = format_episode_list(episodes)

        for episode in episodes:
            assert episode.title in output
            assert f"{episode.index}." in output
