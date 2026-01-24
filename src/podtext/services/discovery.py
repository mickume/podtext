"""Podcast and episode discovery service."""

from datetime import UTC, datetime
from time import struct_time

import feedparser
import httpx

from podtext.core.errors import DiscoveryError
from podtext.core.models import Episode, Podcast

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


class DiscoveryService:
    """Handles podcast and episode discovery."""

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize the discovery service."""
        self.timeout = timeout

    def search_podcasts(self, query: str, limit: int = 10) -> list[Podcast]:
        """
        Search iTunes API for podcasts.

        Args:
            query: Search term
            limit: Maximum number of results (default 10)

        Returns:
            List of Podcast objects matching the search

        Raises:
            DiscoveryError: If the API request fails
        """
        params: dict[str, str | int] = {
            "term": query,
            "media": "podcast",
            "entity": "podcast",
            "limit": limit,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(ITUNES_SEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            raise DiscoveryError(f"Failed to search iTunes API: {e}") from e

        podcasts = []
        for result in data.get("results", []):
            podcast = Podcast(
                title=result.get("collectionName", "Unknown"),
                feed_url=result.get("feedUrl", ""),
                author=result.get("artistName"),
                description=result.get("description"),
                artwork_url=result.get("artworkUrl600") or result.get("artworkUrl100"),
            )
            # Only include podcasts with valid feed URLs
            if podcast.feed_url:
                podcasts.append(podcast)

        return podcasts

    def get_episodes(self, feed_url: str, limit: int = 10) -> list[Episode]:
        """
        Fetch episodes from an RSS feed.

        Args:
            feed_url: URL of the podcast RSS feed
            limit: Maximum number of episodes to return (default 10)

        Returns:
            List of Episode objects (1 = most recent)

        Raises:
            DiscoveryError: If the feed cannot be fetched or parsed
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(feed_url)
                response.raise_for_status()
                content = response.text
        except httpx.HTTPError as e:
            raise DiscoveryError(f"Failed to fetch RSS feed: {e}") from e

        feed = feedparser.parse(content)

        if feed.bozo and not feed.entries:
            raise DiscoveryError(f"Invalid RSS feed: {feed.bozo_exception}")

        episodes = []
        for i, entry in enumerate(feed.entries[:limit], start=1):
            # Find the media URL from enclosures
            media_url = ""
            for enclosure in entry.get("enclosures", []):
                if enclosure.get("type", "").startswith(("audio/", "video/")):
                    media_url = enclosure.get("href", "")
                    break

            # Parse publication date
            published = self._parse_date(entry.get("published_parsed"))

            # Parse duration
            duration = self._parse_duration(entry.get("itunes_duration"))

            episode = Episode(
                index=i,
                title=entry.get("title", "Untitled"),
                published=published,
                media_url=media_url,
                duration=duration,
                description=entry.get("summary"),
            )
            episodes.append(episode)

        return episodes

    def get_podcast_title(self, feed_url: str) -> str:
        """
        Get the podcast title from an RSS feed.

        Args:
            feed_url: URL of the podcast RSS feed

        Returns:
            Podcast title

        Raises:
            DiscoveryError: If the feed cannot be fetched or parsed
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(feed_url)
                response.raise_for_status()
                content = response.text
        except httpx.HTTPError as e:
            raise DiscoveryError(f"Failed to fetch RSS feed: {e}") from e

        feed = feedparser.parse(content)
        return str(feed.feed.get("title", "Unknown Podcast"))

    @staticmethod
    def _parse_date(time_struct: struct_time | None) -> datetime:
        """Parse a time struct to datetime, with fallback to now."""
        if time_struct:
            try:
                from time import mktime

                return datetime.fromtimestamp(mktime(time_struct), tz=UTC)
            except (ValueError, OverflowError):
                pass
        return datetime.now(UTC)

    @staticmethod
    def _parse_duration(duration_str: str | None) -> int | None:
        """Parse duration string to seconds."""
        if not duration_str:
            return None

        try:
            # Handle seconds only
            if duration_str.isdigit():
                return int(duration_str)

            # Handle HH:MM:SS or MM:SS
            parts = duration_str.split(":")
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except (ValueError, TypeError):
            pass

        return None
