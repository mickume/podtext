"""Unit tests for the RSS Feed Parser.

Tests RSS feed parsing, episode extraction, and error handling.

Requirements: 2.1, 2.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from podtext.services.rss import (
    EpisodeInfo,
    RSSFeedError,
    _extract_media_url,
    _parse_feed_entries,
    _parse_pub_date,
    parse_feed,
)


class TestEpisodeInfo:
    """Tests for EpisodeInfo dataclass."""

    def test_create_episode_info(self) -> None:
        """Test creating an EpisodeInfo."""
        pub_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        episode = EpisodeInfo(
            index=1,
            title="Test Episode",
            pub_date=pub_date,
            media_url="https://example.com/episode.mp3",
        )

        assert episode.index == 1
        assert episode.title == "Test Episode"
        assert episode.pub_date == pub_date
        assert episode.media_url == "https://example.com/episode.mp3"

    def test_episode_info_equality(self) -> None:
        """Test that two identical episodes are equal."""
        pub_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        episode1 = EpisodeInfo(
            index=1,
            title="Test Episode",
            pub_date=pub_date,
            media_url="https://example.com/episode.mp3",
        )
        episode2 = EpisodeInfo(
            index=1,
            title="Test Episode",
            pub_date=pub_date,
            media_url="https://example.com/episode.mp3",
        )

        assert episode1 == episode2


class TestParsePubDate:
    """Tests for _parse_pub_date function."""

    def test_parse_rfc2822_date(self) -> None:
        """Test parsing RFC 2822 date format (standard RSS)."""
        date_str = "Mon, 15 Jan 2024 12:00:00 +0000"
        result = _parse_pub_date(date_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_rfc2822_with_timezone(self) -> None:
        """Test parsing RFC 2822 date with timezone."""
        date_str = "Tue, 16 Jan 2024 08:30:00 -0500"
        result = _parse_pub_date(date_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 16

    def test_parse_iso_format(self) -> None:
        """Test parsing ISO format date as fallback."""
        date_str = "2024-01-15T12:00:00Z"
        result = _parse_pub_date(date_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_none_returns_min(self) -> None:
        """Test that None returns datetime.min."""
        result = _parse_pub_date(None)
        assert result == datetime.min

    def test_parse_empty_string_returns_min(self) -> None:
        """Test that empty string returns datetime.min."""
        result = _parse_pub_date("")
        assert result == datetime.min

    def test_parse_invalid_date_returns_min(self) -> None:
        """Test that invalid date returns datetime.min."""
        result = _parse_pub_date("not a date")
        assert result == datetime.min


class TestExtractMediaUrl:
    """Tests for _extract_media_url function."""

    def test_extract_from_enclosure_href(self) -> None:
        """Test extracting media URL from enclosure with href."""
        entry = MagicMock()
        entry.enclosures = [{"href": "https://example.com/episode.mp3"}]
        entry.media_content = []
        entry.links = []

        result = _extract_media_url(entry)
        assert result == "https://example.com/episode.mp3"

    def test_extract_from_enclosure_url(self) -> None:
        """Test extracting media URL from enclosure with url key."""
        entry = MagicMock()
        entry.enclosures = [{"url": "https://example.com/episode.mp3"}]
        entry.media_content = []
        entry.links = []

        result = _extract_media_url(entry)
        assert result == "https://example.com/episode.mp3"

    def test_extract_from_media_content(self) -> None:
        """Test extracting media URL from media_content."""
        entry = MagicMock()
        entry.enclosures = []
        entry.media_content = [{"url": "https://example.com/episode.mp3"}]
        entry.links = []

        result = _extract_media_url(entry)
        assert result == "https://example.com/episode.mp3"

    def test_extract_from_audio_link(self) -> None:
        """Test extracting media URL from audio link."""
        entry = MagicMock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = [{"type": "audio/mpeg", "href": "https://example.com/episode.mp3"}]

        result = _extract_media_url(entry)
        assert result == "https://example.com/episode.mp3"

    def test_extract_from_video_link(self) -> None:
        """Test extracting media URL from video link."""
        entry = MagicMock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = [{"type": "video/mp4", "href": "https://example.com/episode.mp4"}]

        result = _extract_media_url(entry)
        assert result == "https://example.com/episode.mp4"

    def test_extract_no_media_returns_none(self) -> None:
        """Test that missing media returns None."""
        entry = MagicMock()
        entry.enclosures = []
        entry.media_content = []
        entry.links = []

        result = _extract_media_url(entry)
        assert result is None

    def test_extract_prefers_enclosure(self) -> None:
        """Test that enclosure is preferred over other sources."""
        entry = MagicMock()
        entry.enclosures = [{"href": "https://example.com/enclosure.mp3"}]
        entry.media_content = [{"url": "https://example.com/media.mp3"}]
        entry.links = [{"type": "audio/mpeg", "href": "https://example.com/link.mp3"}]

        result = _extract_media_url(entry)
        assert result == "https://example.com/enclosure.mp3"


class TestParseFeedEntries:
    """Tests for _parse_feed_entries function."""

    def test_parse_empty_entries(self) -> None:
        """Test parsing feed with no entries."""
        feed = MagicMock()
        feed.entries = []

        result = _parse_feed_entries(feed, limit=10)
        assert result == []

    def test_parse_single_entry(self) -> None:
        """Test parsing a single entry."""
        entry = MagicMock()
        entry.title = "Episode 1"
        entry.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry.enclosures = [{"href": "https://example.com/ep1.mp3"}]
        entry.media_content = []
        entry.links = []

        feed = MagicMock()
        feed.entries = [entry]

        result = _parse_feed_entries(feed, limit=10)

        assert len(result) == 1
        assert result[0].title == "Episode 1"
        assert result[0].index == 1
        assert result[0].media_url == "https://example.com/ep1.mp3"

    def test_parse_respects_limit(self) -> None:
        """Test that parsing respects the limit parameter."""
        entries = []
        for i in range(5):
            entry = MagicMock()
            entry.title = f"Episode {i + 1}"
            entry.published = f"Mon, {15 + i} Jan 2024 12:00:00 +0000"
            entry.enclosures = [{"href": f"https://example.com/ep{i + 1}.mp3"}]
            entry.media_content = []
            entry.links = []
            entries.append(entry)

        feed = MagicMock()
        feed.entries = entries

        result = _parse_feed_entries(feed, limit=3)
        assert len(result) == 3

    def test_parse_skips_entries_without_title(self) -> None:
        """Test that entries without title are skipped."""
        entry1 = MagicMock()
        entry1.title = "Episode 1"
        entry1.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry1.enclosures = [{"href": "https://example.com/ep1.mp3"}]
        entry1.media_content = []
        entry1.links = []

        entry2 = MagicMock()
        entry2.title = None
        entry2.published = "Tue, 16 Jan 2024 12:00:00 +0000"
        entry2.enclosures = [{"href": "https://example.com/ep2.mp3"}]
        entry2.media_content = []
        entry2.links = []

        feed = MagicMock()
        feed.entries = [entry1, entry2]

        result = _parse_feed_entries(feed, limit=10)
        assert len(result) == 1
        assert result[0].title == "Episode 1"

    def test_parse_skips_entries_without_media(self) -> None:
        """Test that entries without media URL are skipped."""
        entry1 = MagicMock()
        entry1.title = "Episode 1"
        entry1.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry1.enclosures = [{"href": "https://example.com/ep1.mp3"}]
        entry1.media_content = []
        entry1.links = []

        entry2 = MagicMock()
        entry2.title = "Episode 2"
        entry2.published = "Tue, 16 Jan 2024 12:00:00 +0000"
        entry2.enclosures = []
        entry2.media_content = []
        entry2.links = []

        feed = MagicMock()
        feed.entries = [entry1, entry2]

        result = _parse_feed_entries(feed, limit=10)
        assert len(result) == 1
        assert result[0].title == "Episode 1"

    def test_parse_sorts_by_date_descending(self) -> None:
        """Test that episodes are sorted by date (most recent first)."""
        entry1 = MagicMock()
        entry1.title = "Older Episode"
        entry1.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry1.enclosures = [{"href": "https://example.com/ep1.mp3"}]
        entry1.media_content = []
        entry1.links = []

        entry2 = MagicMock()
        entry2.title = "Newer Episode"
        entry2.published = "Wed, 17 Jan 2024 12:00:00 +0000"
        entry2.enclosures = [{"href": "https://example.com/ep2.mp3"}]
        entry2.media_content = []
        entry2.links = []

        feed = MagicMock()
        feed.entries = [entry1, entry2]

        result = _parse_feed_entries(feed, limit=10)

        assert len(result) == 2
        assert result[0].title == "Newer Episode"
        assert result[0].index == 1
        assert result[1].title == "Older Episode"
        assert result[1].index == 2

    def test_parse_uses_updated_as_fallback(self) -> None:
        """Test that 'updated' field is used when 'published' is missing."""
        entry = MagicMock()
        entry.title = "Episode 1"
        entry.published = None
        entry.updated = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry.enclosures = [{"href": "https://example.com/ep1.mp3"}]
        entry.media_content = []
        entry.links = []

        feed = MagicMock()
        feed.entries = [entry]

        result = _parse_feed_entries(feed, limit=10)

        assert len(result) == 1
        assert result[0].pub_date.year == 2024


class TestParseFeed:
    """Tests for parse_feed function.
    
    Validates: Requirements 2.1, 2.5
    """

    def test_parse_empty_url_raises_error(self) -> None:
        """Test that empty URL raises RSSFeedError."""
        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_parse_whitespace_url_raises_error(self) -> None:
        """Test that whitespace-only URL raises RSSFeedError."""
        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("   ")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_parse_zero_limit_returns_empty(self) -> None:
        """Test that zero limit returns empty results."""
        result = parse_feed("https://example.com/feed.xml", limit=0)
        assert result == []

    def test_parse_negative_limit_returns_empty(self) -> None:
        """Test that negative limit returns empty results."""
        result = parse_feed("https://example.com/feed.xml", limit=-5)
        assert result == []

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_parse_successful(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test successful feed parsing.
        
        Validates: Requirement 2.1
        """
        # Setup mock HTTP response
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        # Setup mock feedparser
        entry = MagicMock()
        entry.title = "Test Episode"
        entry.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry.enclosures = [{"href": "https://example.com/episode.mp3"}]
        entry.media_content = []
        entry.links = []

        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feedparser.return_value = mock_feed

        result = parse_feed("https://example.com/feed.xml", limit=10)

        assert len(result) == 1
        assert result[0].title == "Test Episode"
        assert result[0].index == 1
        assert result[0].media_url == "https://example.com/episode.mp3"

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_parse_with_custom_limit(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test parsing with custom limit parameter."""
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        entries = []
        for i in range(10):
            entry = MagicMock()
            entry.title = f"Episode {i + 1}"
            entry.published = f"Mon, {15 + i} Jan 2024 12:00:00 +0000"
            entry.enclosures = [{"href": f"https://example.com/ep{i + 1}.mp3"}]
            entry.media_content = []
            entry.links = []
            entries.append(entry)

        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feedparser.return_value = mock_feed

        result = parse_feed("https://example.com/feed.xml", limit=5)
        assert len(result) == 5

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_parse_strips_url_whitespace(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test that URL whitespace is stripped."""
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        entry = MagicMock()
        entry.title = "Test Episode"
        entry.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry.enclosures = [{"href": "https://example.com/episode.mp3"}]
        entry.media_content = []
        entry.links = []

        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feedparser.return_value = mock_feed

        parse_feed("  https://example.com/feed.xml  ", limit=10)

        mock_client.get.assert_called_once_with("https://example.com/feed.xml")


class TestParseFeedErrorHandling:
    """Tests for error handling in parse_feed.
    
    Validates: Requirement 2.5
    """

    @patch("podtext.services.rss.httpx.Client")
    def test_timeout_error(self, mock_client_class: MagicMock) -> None:
        """Test that timeout raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "timed out" in str(exc_info.value).lower()

    @patch("podtext.services.rss.httpx.Client")
    def test_http_status_error(self, mock_client_class: MagicMock) -> None:
        """Test that HTTP error status raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "404" in str(exc_info.value)

    @patch("podtext.services.rss.httpx.Client")
    def test_connection_error(self, mock_client_class: MagicMock) -> None:
        """Test that connection error raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "Failed to connect" in str(exc_info.value)

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_invalid_feed_with_no_entries(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test that invalid feed with no entries raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_response = MagicMock()
        mock_response.text = "not valid xml"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("XML parsing error")
        mock_feedparser.return_value = mock_feed

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "invalid" in str(exc_info.value).lower()

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_empty_feed_raises_error(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test that feed with no episodes raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_response = MagicMock()
        mock_response.text = "<rss></rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feedparser.return_value = mock_feed

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "no episodes" in str(exc_info.value).lower()

    @patch("podtext.services.rss.httpx.Client")
    def test_request_error(self, mock_client_class: MagicMock) -> None:
        """Test that generic request error raises RSSFeedError.
        
        Validates: Requirement 2.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("Network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(RSSFeedError) as exc_info:
            parse_feed("https://example.com/feed.xml")

        assert "Failed to connect" in str(exc_info.value)

    @patch("podtext.services.rss.httpx.Client")
    @patch("podtext.services.rss.feedparser.parse")
    def test_bozo_feed_with_entries_continues(
        self, mock_feedparser: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Test that malformed feed with entries still parses.
        
        Some feeds are technically malformed but still parseable.
        """
        mock_response = MagicMock()
        mock_response.text = "<rss>...</rss>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        entry = MagicMock()
        entry.title = "Test Episode"
        entry.published = "Mon, 15 Jan 2024 12:00:00 +0000"
        entry.enclosures = [{"href": "https://example.com/episode.mp3"}]
        entry.media_content = []
        entry.links = []

        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_feed.bozo = True  # Malformed but has entries
        mock_feed.bozo_exception = Exception("Minor XML issue")
        mock_feedparser.return_value = mock_feed

        # Should not raise, should return episodes
        result = parse_feed("https://example.com/feed.xml")
        assert len(result) == 1
        assert result[0].title == "Test Episode"
