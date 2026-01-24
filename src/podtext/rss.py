"""RSS feed parser for podcast episodes.

Parses podcast RSS feeds to extract episode information.
"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser

from .models import EpisodeInfo


class RSSParseError(Exception):
    """Error parsing RSS feed."""

    pass


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse an RSS date string to datetime."""
    if not date_str:
        return None

    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass

    # Try common alternative formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def _get_media_url(entry: dict) -> Optional[str]:
    """Extract media URL from feed entry."""
    # Check enclosures first (standard podcast format)
    enclosures = entry.get("enclosures", [])
    for enclosure in enclosures:
        url = enclosure.get("href") or enclosure.get("url")
        media_type = enclosure.get("type", "")
        if url and ("audio" in media_type or url.endswith((".mp3", ".m4a", ".wav", ".ogg"))):
            return url

    # Check media content
    media_content = entry.get("media_content", [])
    for media in media_content:
        url = media.get("url")
        media_type = media.get("type", "")
        if url and ("audio" in media_type or url.endswith((".mp3", ".m4a", ".wav", ".ogg"))):
            return url

    # Check links
    links = entry.get("links", [])
    for link in links:
        url = link.get("href")
        link_type = link.get("type", "")
        if url and ("audio" in link_type or "enclosure" in link.get("rel", "")):
            return url

    return None


def parse_feed(feed_url: str, limit: int = 10) -> list[EpisodeInfo]:
    """Parse podcast RSS feed and return episode information.

    Args:
        feed_url: URL of the podcast RSS feed.
        limit: Maximum number of episodes to return (default 10).

    Returns:
        List of EpisodeInfo objects, sorted by publication date (newest first).

    Raises:
        RSSParseError: If the feed is invalid or unreachable.
    """
    if limit <= 0:
        return []

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        raise RSSParseError(f"Failed to parse RSS feed: {e}") from e

    # Check for parse errors
    if feed.bozo and feed.bozo_exception:
        # feedparser sets bozo=1 for any parsing issue, but some are recoverable
        if not feed.entries:
            raise RSSParseError(f"Invalid RSS feed: {feed.bozo_exception}")

    if not feed.entries:
        raise RSSParseError("RSS feed contains no episodes")

    episodes = []
    for entry in feed.entries:
        title = entry.get("title")
        if not title:
            continue

        pub_date_str = entry.get("published") or entry.get("updated")
        pub_date = _parse_date(pub_date_str) if pub_date_str else None

        if not pub_date:
            # Use a fallback date if none available
            pub_date = datetime.now()

        media_url = _get_media_url(entry)
        if not media_url:
            continue

        episodes.append(EpisodeInfo(
            index=0,  # Will be assigned after sorting
            title=title,
            pub_date=pub_date,
            media_url=media_url,
        ))

    # Sort by publication date (newest first)
    episodes.sort(key=lambda e: e.pub_date, reverse=True)

    # Limit results and assign indices
    episodes = episodes[:limit]
    for i, episode in enumerate(episodes):
        episode.index = i + 1

    return episodes
