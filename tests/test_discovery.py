"""Tests for discovery service."""

import pytest
import respx
from httpx import Response

from podtext.core.errors import DiscoveryError
from podtext.services.discovery import DiscoveryService


class TestDiscoveryServiceSearch:
    """Tests for podcast search functionality."""

    @respx.mock
    def test_search_podcasts_success(self, sample_itunes_response: dict) -> None:
        """Test successful podcast search."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=Response(200, json=sample_itunes_response)
        )

        service = DiscoveryService()
        podcasts = service.search_podcasts("test")

        assert len(podcasts) == 2
        assert podcasts[0].title == "Test Podcast"
        assert podcasts[0].feed_url == "https://example.com/feed.xml"
        assert podcasts[0].author == "Test Author"

    @respx.mock
    def test_search_podcasts_with_limit(self) -> None:
        """Test search with limit parameter."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {
                            "collectionName": "Single Podcast",
                            "feedUrl": "https://example.com/feed.xml",
                        }
                    ],
                },
            )
        )

        service = DiscoveryService()
        podcasts = service.search_podcasts("test", limit=1)

        assert len(podcasts) == 1

    @respx.mock
    def test_search_podcasts_empty_results(self) -> None:
        """Test search with no results."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=Response(200, json={"resultCount": 0, "results": []})
        )

        service = DiscoveryService()
        podcasts = service.search_podcasts("nonexistent")

        assert podcasts == []

    @respx.mock
    def test_search_podcasts_api_error(self) -> None:
        """Test search with API error."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=Response(500)
        )

        service = DiscoveryService()
        with pytest.raises(DiscoveryError) as exc_info:
            service.search_podcasts("test")

        assert "Failed to search iTunes API" in str(exc_info.value)

    @respx.mock
    def test_search_podcasts_skips_missing_feed_url(self) -> None:
        """Test that podcasts without feed URLs are skipped."""
        respx.get("https://itunes.apple.com/search").mock(
            return_value=Response(
                200,
                json={
                    "resultCount": 2,
                    "results": [
                        {
                            "collectionName": "Has Feed",
                            "feedUrl": "https://example.com/feed.xml",
                        },
                        {
                            "collectionName": "No Feed",
                            # Missing feedUrl
                        },
                    ],
                },
            )
        )

        service = DiscoveryService()
        podcasts = service.search_podcasts("test")

        assert len(podcasts) == 1
        assert podcasts[0].title == "Has Feed"


class TestDiscoveryServiceEpisodes:
    """Tests for episode fetching functionality."""

    @respx.mock
    def test_get_episodes_success(self, sample_rss_feed: str) -> None:
        """Test successful episode fetching."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=Response(200, text=sample_rss_feed)
        )

        service = DiscoveryService()
        episodes = service.get_episodes("https://example.com/feed.xml")

        assert len(episodes) == 2
        assert episodes[0].index == 1
        assert episodes[0].title == "Episode 1"
        assert episodes[0].media_url == "https://example.com/ep1.mp3"
        assert episodes[0].duration == 1800  # 30:00

    @respx.mock
    def test_get_episodes_with_limit(self, sample_rss_feed: str) -> None:
        """Test episode fetching with limit."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=Response(200, text=sample_rss_feed)
        )

        service = DiscoveryService()
        episodes = service.get_episodes("https://example.com/feed.xml", limit=1)

        assert len(episodes) == 1
        assert episodes[0].title == "Episode 1"

    @respx.mock
    def test_get_episodes_feed_error(self) -> None:
        """Test episode fetching with feed error."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=Response(404)
        )

        service = DiscoveryService()
        with pytest.raises(DiscoveryError) as exc_info:
            service.get_episodes("https://example.com/feed.xml")

        assert "Failed to fetch RSS feed" in str(exc_info.value)

    @respx.mock
    def test_get_podcast_title(self, sample_rss_feed: str) -> None:
        """Test getting podcast title from feed."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=Response(200, text=sample_rss_feed)
        )

        service = DiscoveryService()
        title = service.get_podcast_title("https://example.com/feed.xml")

        assert title == "Test Podcast"


class TestDurationParsing:
    """Tests for duration parsing."""

    def test_parse_duration_seconds(self) -> None:
        """Test parsing duration as seconds."""
        assert DiscoveryService._parse_duration("120") == 120

    def test_parse_duration_mmss(self) -> None:
        """Test parsing MM:SS format."""
        assert DiscoveryService._parse_duration("30:00") == 1800

    def test_parse_duration_hhmmss(self) -> None:
        """Test parsing HH:MM:SS format."""
        assert DiscoveryService._parse_duration("1:30:00") == 5400

    def test_parse_duration_none(self) -> None:
        """Test parsing None duration."""
        assert DiscoveryService._parse_duration(None) is None

    def test_parse_duration_invalid(self) -> None:
        """Test parsing invalid duration."""
        assert DiscoveryService._parse_duration("invalid") is None
