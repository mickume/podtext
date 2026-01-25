"""RSS Feed Parser for podcast episode discovery.

Provides functionality to parse podcast RSS feeds and extract episode information.

Requirements: 2.1, 2.5
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

# Default timeout for feed requests (in seconds)
DEFAULT_TIMEOUT = 30.0


class RSSFeedError(Exception):
    """Raised when the RSS feed is invalid or unreachable.
    
    Validates: Requirement 2.5
    """


@dataclass
class EpisodeInfo:
    """Represents a podcast episode from an RSS feed.
    
    Attributes:
        index: The index number assigned to the episode (1-based, most recent first).
        title: The title of the episode.
        pub_date: The publication date of the episode.
        media_url: The URL to the episode's media file (audio/video).
        feed_url: The RSS feed URL from which this episode was discovered (optional).
    """
    
    index: int
    title: str
    pub_date: datetime
    media_url: str
    feed_url: str | None = None


def _parse_pub_date(date_str: str | None) -> datetime:
    """Parse a publication date string from RSS feed.
    
    RSS feeds typically use RFC 2822 date format.
    
    Args:
        date_str: The date string from the RSS feed.
        
    Returns:
        Parsed datetime object, or datetime.min if parsing fails.
    """
    if not date_str:
        return datetime.min
    
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        # Try ISO format as fallback
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.min


def _extract_media_url(entry: Any) -> str | None:
    """Extract the media URL from an RSS feed entry.
    
    Looks for enclosures (standard podcast format) or media content.
    
    Args:
        entry: A feedparser entry object.
        
    Returns:
        The media URL if found, None otherwise.
    """
    # Check enclosures first (standard for podcasts)
    enclosures = getattr(entry, "enclosures", [])
    for enclosure in enclosures:
        href = enclosure.get("href") or enclosure.get("url")
        if href:
            return str(href)
    
    # Check media content as fallback
    media_content = getattr(entry, "media_content", [])
    for media in media_content:
        url = media.get("url")
        if url:
            return str(url)
    
    # Check for links with audio/video type
    links = getattr(entry, "links", [])
    for link in links:
        link_type = link.get("type", "")
        if "audio" in link_type or "video" in link_type:
            href = link.get("href")
            if href:
                return str(href)
    
    return None


def _parse_feed_entries(
    feed: Any,
    limit: int,
    feed_url: str = "",
) -> list[EpisodeInfo]:
    """Parse feed entries into EpisodeInfo objects.
    
    Args:
        feed: A feedparser parsed feed object.
        limit: Maximum number of episodes to return.
        feed_url: The RSS feed URL to include in each episode.
        
    Returns:
        List of EpisodeInfo objects, sorted by publication date (most recent first).
    """
    episodes: list[EpisodeInfo] = []
    
    entries = feed.entries[:limit] if limit > 0 else []
    
    for entry in entries:
        title = getattr(entry, "title", None)
        if not title:
            continue
        
        media_url = _extract_media_url(entry)
        if not media_url:
            continue
        
        pub_date_str = getattr(entry, "published", None) or getattr(entry, "updated", None)
        pub_date = _parse_pub_date(pub_date_str)
        
        episodes.append(
            EpisodeInfo(
                index=0,  # Will be assigned after sorting
                title=str(title),
                pub_date=pub_date,
                media_url=str(media_url),
                feed_url=feed_url if feed_url else None,
            )
        )
    
    # Sort by publication date (most recent first)
    episodes.sort(key=lambda e: e.pub_date, reverse=True)
    
    # Assign index numbers (1-based)
    for i, episode in enumerate(episodes, start=1):
        episode.index = i
    
    return episodes


def parse_feed(
    feed_url: str,
    limit: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[EpisodeInfo]:
    """Parse a podcast RSS feed and extract episode information.
    
    Retrieves the RSS feed from the given URL and extracts episode information
    including title, publication date, and media URL. Episodes are sorted by
    publication date (most recent first) and assigned index numbers.
    
    Args:
        feed_url: URL of the podcast RSS feed.
        limit: Maximum number of episodes to return (default: 10).
        timeout: Request timeout in seconds (default: 30.0).
        
    Returns:
        List of EpisodeInfo objects containing episode details.
        
    Raises:
        RSSFeedError: If the feed is invalid, unreachable, or cannot be parsed.
        
    Validates: Requirements 2.1, 2.5
    
    Example:
        >>> episodes = parse_feed("https://example.com/podcast/feed.xml", limit=5)
        >>> for ep in episodes:
        ...     print(f"{ep.index}. {ep.title} ({ep.pub_date.date()})")
    """
    if not feed_url or not feed_url.strip():
        raise RSSFeedError("Feed URL cannot be empty")
    
    # Ensure limit is positive
    if limit <= 0:
        return []
    
    feed_url = feed_url.strip()
    
    # Fetch the feed content using httpx for better error handling
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(feed_url)
            response.raise_for_status()
            feed_content = response.text
            
    except httpx.TimeoutException as e:
        raise RSSFeedError(
            f"RSS feed request timed out after {timeout} seconds"
        ) from e
        
    except httpx.HTTPStatusError as e:
        raise RSSFeedError(
            f"RSS feed returned error status {e.response.status_code}: {e.response.text[:200]}"
        ) from e
        
    except httpx.RequestError as e:
        raise RSSFeedError(
            f"Failed to connect to RSS feed: {e}"
        ) from e
    
    # Parse the feed content
    try:
        feed = feedparser.parse(feed_content)
    except Exception as e:
        raise RSSFeedError(f"Failed to parse RSS feed: {e}") from e
    
    # Check for feed-level errors
    if feed.bozo and feed.bozo_exception:
        # feedparser sets bozo=True for malformed feeds
        # Some feeds are technically malformed but still parseable
        # Only raise if we have no entries
        if not feed.entries:
            raise RSSFeedError(
                f"Invalid RSS feed: {feed.bozo_exception}"
            )
    
    # Check if feed has any entries
    if not feed.entries:
        raise RSSFeedError("RSS feed contains no episodes")
    
    return _parse_feed_entries(feed, limit, feed_url)
