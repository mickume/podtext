"""Tests for RSS feed parser.

Feature: podtext
Property 1: Result Limiting (for episodes)
Property 4: RSS Parsing Validity
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone
import tempfile
from pathlib import Path

from podtext.rss import parse_feed, RSSParseError, _parse_date, _get_media_url
from podtext.models import EpisodeInfo


# Sample RSS feed template
RSS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Podcast</title>
    <description>A test podcast</description>
    {items}
  </channel>
</rss>
"""

ITEM_TEMPLATE = """\
<item>
  <title>{title}</title>
  <pubDate>{pub_date}</pubDate>
  <enclosure url="{media_url}" type="audio/mpeg" length="12345"/>
</item>
"""


def create_rss_feed(items: list[dict]) -> str:
    """Create an RSS feed string from item data."""
    items_xml = "\n".join(
        ITEM_TEMPLATE.format(
            title=item.get("title", "Episode"),
            pub_date=item.get("pub_date", "Mon, 01 Jan 2024 00:00:00 +0000"),
            media_url=item.get("media_url", "https://example.com/episode.mp3"),
        )
        for item in items
    )
    return RSS_TEMPLATE.format(items=items_xml)


def save_feed_to_file(content: str) -> Path:
    """Save RSS content to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(content)
        return Path(f.name)


class TestParseDateHelper:
    """Tests for date parsing helper."""

    def test_parse_rfc822_date(self):
        """Test parsing RFC 822 format."""
        result = _parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_parse_iso_format(self):
        """Test parsing ISO 8601 format."""
        result = _parse_date("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        assert _parse_date("") is None

    def test_parse_invalid_date(self):
        """Test parsing invalid date returns None."""
        assert _parse_date("not a date") is None


class TestGetMediaUrl:
    """Tests for media URL extraction."""

    def test_extract_from_enclosure(self):
        """Test extracting URL from enclosure."""
        entry = {
            "enclosures": [{"href": "https://example.com/ep.mp3", "type": "audio/mpeg"}]
        }
        assert _get_media_url(entry) == "https://example.com/ep.mp3"

    def test_extract_from_media_content(self):
        """Test extracting URL from media_content."""
        entry = {
            "media_content": [{"url": "https://example.com/ep.mp3", "type": "audio/mpeg"}]
        }
        assert _get_media_url(entry) == "https://example.com/ep.mp3"

    def test_extract_by_extension(self):
        """Test extracting URL by file extension."""
        entry = {
            "enclosures": [{"href": "https://example.com/episode.mp3"}]
        }
        assert _get_media_url(entry) == "https://example.com/episode.mp3"

    def test_no_media_url(self):
        """Test that None is returned when no media URL found."""
        entry = {"links": [{"href": "https://example.com/page"}]}
        assert _get_media_url(entry) is None


class TestParseFeedBasics:
    """Basic feed parsing tests."""

    def test_parse_valid_feed(self):
        """Test parsing a valid RSS feed."""
        feed_content = create_rss_feed([
            {"title": "Episode 1", "pub_date": "Mon, 15 Jan 2024 12:00:00 +0000"},
            {"title": "Episode 2", "pub_date": "Tue, 16 Jan 2024 12:00:00 +0000"},
        ])
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))

            assert len(episodes) == 2
            assert all(isinstance(e, EpisodeInfo) for e in episodes)
            # Should be sorted newest first
            assert episodes[0].title == "Episode 2"
            assert episodes[1].title == "Episode 1"
        finally:
            feed_path.unlink()

    def test_parse_assigns_indices(self):
        """Test that episodes are assigned sequential indices."""
        feed_content = create_rss_feed([
            {"title": "Episode 1"},
            {"title": "Episode 2"},
            {"title": "Episode 3"},
        ])
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))

            assert [e.index for e in episodes] == [1, 2, 3]
        finally:
            feed_path.unlink()

    def test_parse_skips_items_without_title(self):
        """Test that items without title are skipped."""
        feed_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>Has Title</title>
      <enclosure url="https://example.com/ep.mp3" type="audio/mpeg"/>
    </item>
    <item>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg"/>
    </item>
  </channel>
</rss>
"""
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))
            assert len(episodes) == 1
            assert episodes[0].title == "Has Title"
        finally:
            feed_path.unlink()

    def test_parse_skips_items_without_media(self):
        """Test that items without media URL are skipped."""
        feed_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>Has Media</title>
      <enclosure url="https://example.com/ep.mp3" type="audio/mpeg"/>
    </item>
    <item>
      <title>No Media</title>
    </item>
  </channel>
</rss>
"""
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))
            assert len(episodes) == 1
            assert episodes[0].title == "Has Media"
        finally:
            feed_path.unlink()

    def test_parse_empty_feed_raises_error(self):
        """Test that empty feed raises RSSParseError."""
        feed_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Podcast</title>
  </channel>
</rss>
"""
        feed_path = save_feed_to_file(feed_content)

        try:
            with pytest.raises(RSSParseError, match="no episodes"):
                parse_feed(str(feed_path))
        finally:
            feed_path.unlink()

    def test_parse_with_zero_limit(self):
        """Test that zero limit returns empty list."""
        feed_content = create_rss_feed([{"title": "Episode 1"}])
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path), limit=0)
            assert episodes == []
        finally:
            feed_path.unlink()


class TestProperty1ResultLimiting:
    """Property 1: Result Limiting for episodes.

    For any episode listing operation with limit N, the returned results SHALL have length ≤ N.

    Validates: Requirements 2.3, 2.4
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        limit=st.integers(min_value=1, max_value=20),
        num_episodes=st.integers(min_value=1, max_value=30),
    )
    def test_episodes_respect_limit(self, limit, num_episodes):
        """Episode listing never exceeds the specified limit."""
        items = [
            {"title": f"Episode {i}", "pub_date": f"Mon, {i:02d} Jan 2024 12:00:00 +0000"}
            for i in range(1, num_episodes + 1)
        ]
        feed_content = create_rss_feed(items)
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path), limit=limit)
            assert len(episodes) <= limit
        finally:
            feed_path.unlink()


class TestProperty4RSSParsingValidity:
    """Property 4: RSS Parsing Validity.

    For any valid RSS feed XML, parsing then extracting episode info SHALL produce
    EpisodeInfo objects with non-empty title, valid datetime, and valid media URL.

    Validates: Requirements 2.1
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title=st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "S"),
            blacklist_characters='<>&"'
        )),
        day=st.integers(min_value=1, max_value=28),
    )
    def test_parsed_episodes_have_valid_fields(self, title, day):
        """Parsed episodes have non-empty title, valid datetime, and valid media URL."""
        pub_date = f"Mon, {day:02d} Jan 2024 12:00:00 +0000"
        media_url = "https://example.com/episode.mp3"

        items = [{"title": title, "pub_date": pub_date, "media_url": media_url}]
        feed_content = create_rss_feed(items)
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))

            assert len(episodes) == 1
            episode = episodes[0]

            # Verify non-empty title
            assert episode.title
            assert len(episode.title) > 0

            # Verify valid datetime
            assert isinstance(episode.pub_date, datetime)

            # Verify valid media URL
            assert episode.media_url
            assert episode.media_url.startswith("http")
        finally:
            feed_path.unlink()

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(num_episodes=st.integers(min_value=1, max_value=10))
    def test_all_episodes_have_indices(self, num_episodes):
        """All parsed episodes have valid index numbers starting from 1."""
        items = [
            {"title": f"Episode {i}"}
            for i in range(num_episodes)
        ]
        feed_content = create_rss_feed(items)
        feed_path = save_feed_to_file(feed_content)

        try:
            episodes = parse_feed(str(feed_path))

            # All episodes should have indices from 1 to len
            indices = [e.index for e in episodes]
            assert indices == list(range(1, len(episodes) + 1))
        finally:
            feed_path.unlink()
