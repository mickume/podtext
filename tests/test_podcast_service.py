"""Tests for podcast service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import httpx
import respx

from podtext.models.podcast import Podcast
from podtext.services.podcast import PodcastService, PodcastError


SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
    <title>Test Podcast</title>
    <language>en</language>
    <item>
        <title>Episode 3</title>
        <pubDate>Wed, 20 Mar 2024 10:00:00 GMT</pubDate>
        <enclosure url="https://example.com/ep3.mp3" type="audio/mpeg" length="1000000"/>
        <itunes:duration>30:00</itunes:duration>
    </item>
    <item>
        <title>Episode 2</title>
        <pubDate>Wed, 13 Mar 2024 10:00:00 GMT</pubDate>
        <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="1000000"/>
        <itunes:duration>1:00:00</itunes:duration>
    </item>
    <item>
        <title>Episode 1</title>
        <pubDate>Wed, 06 Mar 2024 10:00:00 GMT</pubDate>
        <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="1000000"/>
        <itunes:duration>2700</itunes:duration>
    </item>
</channel>
</rss>
"""


class TestPodcastService:
    """Tests for PodcastService."""

    def test_search_delegates_to_itunes_client(self):
        """Test that search delegates to iTunes client."""
        mock_client = MagicMock()
        mock_client.search_podcasts.return_value = [
            Podcast(title="Test", feed_url="https://example.com/feed.xml")
        ]

        service = PodcastService(itunes_client=mock_client)
        results = service.search("test", limit=5)

        mock_client.search_podcasts.assert_called_once_with("test", 5)
        assert len(results) == 1

    @respx.mock
    def test_get_episodes_success(self):
        """Test getting episodes from RSS feed."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()
        episodes = service.get_episodes("https://example.com/feed.xml", limit=10)

        assert len(episodes) == 3
        # Should be sorted by date (most recent first)
        assert episodes[0].title == "Episode 3"
        assert episodes[1].title == "Episode 2"
        assert episodes[2].title == "Episode 1"

    @respx.mock
    def test_get_episodes_respects_limit(self):
        """Test that limit is respected."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()
        episodes = service.get_episodes("https://example.com/feed.xml", limit=2)

        assert len(episodes) == 2

    @respx.mock
    def test_get_episodes_parses_duration(self):
        """Test duration parsing."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()
        episodes = service.get_episodes("https://example.com/feed.xml", limit=10)

        # Episode 3: "30:00" = 1800 seconds
        assert episodes[0].duration == 1800
        # Episode 2: "1:00:00" = 3600 seconds
        assert episodes[1].duration == 3600
        # Episode 1: "2700" seconds
        assert episodes[2].duration == 2700

    @respx.mock
    def test_get_episode_by_index(self):
        """Test getting episode by index."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()
        # First, get episodes to populate cache
        service.get_episodes("https://example.com/feed.xml", limit=10)

        # Get specific episode
        episode = service.get_episode_by_index("https://example.com/feed.xml", 2, limit=10)
        assert episode.title == "Episode 2"

    @respx.mock
    def test_get_episode_by_index_out_of_range(self):
        """Test error when index is out of range."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()

        with pytest.raises(PodcastError) as exc_info:
            service.get_episode_by_index("https://example.com/feed.xml", 10, limit=3)

        assert "out of range" in str(exc_info.value).lower()

    @respx.mock
    def test_get_podcast_name(self):
        """Test getting podcast name from feed."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=SAMPLE_RSS_FEED)
        )

        service = PodcastService()
        name = service.get_podcast_name("https://example.com/feed.xml")

        assert name == "Test Podcast"

    @respx.mock
    def test_get_episodes_handles_fetch_error(self):
        """Test error handling for feed fetch failure."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(404)
        )

        service = PodcastService()

        with pytest.raises(PodcastError):
            service.get_episodes("https://example.com/feed.xml")


class TestRSSParsing:
    """Tests for RSS feed parsing edge cases."""

    @respx.mock
    def test_parse_feed_without_enclosure(self):
        """Test parsing feed items without proper enclosures."""
        feed = """<?xml version="1.0"?>
        <rss version="2.0">
        <channel>
            <title>No Audio</title>
            <item>
                <title>Text Only</title>
                <pubDate>Wed, 20 Mar 2024 10:00:00 GMT</pubDate>
            </item>
        </channel>
        </rss>
        """
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=feed)
        )

        service = PodcastService()
        episodes = service.get_episodes("https://example.com/feed.xml")

        # Episode without media URL should be skipped
        assert len(episodes) == 0

    @respx.mock
    def test_parse_feed_with_media_content(self):
        """Test parsing feed with media:content instead of enclosure."""
        feed = """<?xml version="1.0"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
        <channel>
            <title>Media Content</title>
            <item>
                <title>Episode</title>
                <pubDate>Wed, 20 Mar 2024 10:00:00 GMT</pubDate>
                <media:content url="https://example.com/ep.mp3" type="audio/mpeg"/>
            </item>
        </channel>
        </rss>
        """
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=feed)
        )

        service = PodcastService()
        episodes = service.get_episodes("https://example.com/feed.xml")

        assert len(episodes) == 1
        assert episodes[0].media_url == "https://example.com/ep.mp3"
