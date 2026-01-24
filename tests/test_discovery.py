"""Tests for discovery module (iTunes API and RSS parsing).

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import json
from datetime import datetime

import httpx
import pytest
import respx
from hypothesis import given, settings, strategies as st

from podtext.itunes import (
    ITunesAPIError,
    format_search_results,
    search_podcasts,
)
from podtext.models import EpisodeInfo, PodcastSearchResult
from podtext.rss import (
    RSSParseError,
    format_episodes,
    get_episode_by_index,
    parse_feed,
)


# Strategies for generating test data
title_strategy = st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")))
url_strategy = st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N")))


def generate_itunes_response(count: int) -> dict:
    """Generate a mock iTunes API response with specified number of results."""
    results = []
    for i in range(count):
        results.append({
            "collectionName": f"Podcast {i + 1}",
            "feedUrl": f"https://example.com/feed{i + 1}.xml",
            "trackName": f"Track {i + 1}",
        })
    return {"resultCount": count, "results": results}


def generate_rss_feed(episodes: list[dict]) -> str:
    """Generate a mock RSS feed XML with specified episodes."""
    items = []
    for ep in episodes:
        items.append(f"""
        <item>
            <title>{ep.get('title', 'Episode')}</title>
            <pubDate>{ep.get('pub_date', 'Mon, 01 Jan 2024 00:00:00 +0000')}</pubDate>
            <enclosure url="{ep.get('media_url', 'https://example.com/audio.mp3')}" type="audio/mpeg" length="1234567"/>
        </item>
        """)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Podcast</title>
            <description>A test podcast</description>
            {"".join(items)}
        </channel>
    </rss>
    """


class TestResultLimiting:
    """
    Property 1: Result Limiting

    For any search or episode listing operation with limit N,
    the returned results SHALL have length ≤ N.

    Validates: Requirements 1.3, 1.4, 2.3, 2.4
    """

    @settings(max_examples=100)
    @given(
        limit=st.integers(min_value=1, max_value=50),
        result_count=st.integers(min_value=0, max_value=100),
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_search_results_respect_limit(self, limit: int, result_count: int) -> None:
        """Property 1: Search results length <= limit."""
        # Mock iTunes API response
        response_data = generate_itunes_response(result_count)
        respx.get("https://itunes.apple.com/search").mock(
            return_value=httpx.Response(200, json=response_data)
        )

        results = await search_podcasts("test", limit=limit)

        assert len(results) <= limit, (
            f"Expected at most {limit} results, got {len(results)}"
        )

    @settings(max_examples=100)
    @given(
        limit=st.integers(min_value=1, max_value=50),
        episode_count=st.integers(min_value=0, max_value=100),
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_episode_results_respect_limit(self, limit: int, episode_count: int) -> None:
        """Property 1: Episode listing length <= limit."""
        # Generate episodes
        episodes = [
            {
                "title": f"Episode {i}",
                "pub_date": "Mon, 01 Jan 2024 00:00:00 +0000",
                "media_url": f"https://example.com/ep{i}.mp3",
            }
            for i in range(episode_count)
        ]
        feed_xml = generate_rss_feed(episodes)

        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=feed_xml)
        )

        results = await parse_feed("https://example.com/feed.xml", limit=limit)

        assert len(results) <= limit, (
            f"Expected at most {limit} episodes, got {len(results)}"
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
                "feed_url": st.text(min_size=10, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/:.-_"),
            }),
            min_size=1,
            max_size=20,
        )
    )
    def test_search_results_display_contains_all_fields(self, items: list[dict]) -> None:
        """Property 2: Formatted output contains title and feed_url for each result."""
        results = [
            PodcastSearchResult(title=item["title"], feed_url=item["feed_url"])
            for item in items
        ]

        output = format_search_results(results)

        for result in results:
            assert result.title in output, (
                f"Title '{result.title}' not found in output"
            )
            assert result.feed_url in output, (
                f"Feed URL '{result.feed_url}' not found in output"
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
                "days_ago": st.integers(min_value=0, max_value=3650),
            }),
            min_size=1,
            max_size=20,
            unique_by=lambda x: x["index"],
        )
    )
    def test_episode_display_contains_all_fields(self, items: list[dict]) -> None:
        """Property 3: Formatted output contains title, date, and index for each episode."""
        episodes = [
            EpisodeInfo(
                index=item["index"],
                title=item["title"],
                pub_date=datetime(2024, 1, 1),  # Fixed date for testing
                media_url="https://example.com/audio.mp3",
            )
            for item in items
        ]

        output = format_episodes(episodes)

        for episode in episodes:
            # Check index is present (as the leading number)
            assert f"{episode.index}." in output, (
                f"Index '{episode.index}' not found in output"
            )
            assert episode.title in output, (
                f"Title '{episode.title}' not found in output"
            )
            # Check date format
            date_str = episode.pub_date.strftime("%Y-%m-%d")
            assert date_str in output, (
                f"Publication date '{date_str}' not found in output"
            )


class TestRSSParsingValidity:
    """
    Property 4: RSS Parsing Validity

    For any valid RSS feed XML, parsing then extracting episode info
    SHALL produce EpisodeInfo objects with non-empty title, valid datetime, and valid media URL.

    Validates: Requirements 2.1
    """

    @settings(max_examples=100)
    @given(
        episode_titles=st.lists(
            st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "),
            min_size=1,
            max_size=10,
        ),
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_parsed_episodes_have_valid_fields(self, episode_titles: list[str]) -> None:
        """Property 4: Parsed episodes have non-empty title, valid datetime, valid media URL."""
        episodes = [
            {
                "title": title,
                "pub_date": "Mon, 15 Jan 2024 12:00:00 +0000",
                "media_url": f"https://example.com/ep{i}.mp3",
            }
            for i, title in enumerate(episode_titles)
        ]
        feed_xml = generate_rss_feed(episodes)

        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=feed_xml)
        )

        results = await parse_feed("https://example.com/feed.xml", limit=100)

        for episode in results:
            # Non-empty title
            assert episode.title, "Episode title should not be empty"

            # Valid datetime
            assert isinstance(episode.pub_date, datetime), "pub_date should be a datetime"

            # Valid media URL
            assert episode.media_url, "Media URL should not be empty"
            assert episode.media_url.startswith("http"), (
                f"Media URL should be valid: {episode.media_url}"
            )


class TestITunesAPIErrorHandling:
    """Tests for iTunes API error handling."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_itunes_api_http_error(self) -> None:
        """iTunes API HTTP errors should raise ITunesAPIError."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=httpx.Response(500)
        )

        with pytest.raises(ITunesAPIError) as exc_info:
            await search_podcasts("test")

        assert "error status" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_itunes_api_connection_error(self) -> None:
        """iTunes API connection errors should raise ITunesAPIError."""
        respx.get("https://itunes.apple.com/search").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(ITunesAPIError) as exc_info:
            await search_podcasts("test")

        assert "Failed to connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_itunes_api_invalid_json(self) -> None:
        """Invalid JSON response should raise ITunesAPIError."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=httpx.Response(200, text="not json")
        )

        with pytest.raises(ITunesAPIError) as exc_info:
            await search_podcasts("test")

        assert "Invalid JSON" in str(exc_info.value)


class TestRSSParseErrorHandling:
    """Tests for RSS parsing error handling."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_rss_feed_http_error(self) -> None:
        """RSS feed HTTP errors should raise RSSParseError."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(404)
        )

        with pytest.raises(RSSParseError) as exc_info:
            await parse_feed("https://example.com/feed.xml")

        assert "404" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_rss_feed_connection_error(self) -> None:
        """RSS feed connection errors should raise RSSParseError."""
        respx.get("https://example.com/feed.xml").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(RSSParseError) as exc_info:
            await parse_feed("https://example.com/feed.xml")

        assert "Failed to connect" in str(exc_info.value)


class TestEpisodeIndexLookup:
    """Tests for episode lookup by index."""

    def test_get_episode_by_index_found(self) -> None:
        """Should return episode when index exists."""
        episodes = [
            EpisodeInfo(
                index=i,
                title=f"Episode {i}",
                pub_date=datetime.now(),
                media_url=f"https://example.com/ep{i}.mp3",
            )
            for i in range(1, 4)
        ]

        result = get_episode_by_index(episodes, 2)

        assert result is not None
        assert result.index == 2
        assert result.title == "Episode 2"

    def test_get_episode_by_index_not_found(self) -> None:
        """Should return None when index doesn't exist."""
        episodes = [
            EpisodeInfo(
                index=1,
                title="Episode 1",
                pub_date=datetime.now(),
                media_url="https://example.com/ep1.mp3",
            )
        ]

        result = get_episode_by_index(episodes, 99)

        assert result is None


class TestEmptyResults:
    """Tests for empty result handling."""

    def test_empty_search_results_format(self) -> None:
        """Empty search results should display message."""
        output = format_search_results([])
        assert "No podcasts found" in output

    def test_empty_episodes_format(self) -> None:
        """Empty episode list should display message."""
        output = format_episodes([])
        assert "No episodes found" in output
