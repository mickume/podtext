"""Podcast service for discovery and RSS parsing."""

import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from podtext.clients.itunes import iTunesClient
from podtext.models.podcast import Episode, Podcast


class PodcastError(Exception):
    """Exception raised for podcast service errors."""

    pass


class PodcastService:
    """Service for podcast discovery and episode management."""

    def __init__(self, itunes_client: iTunesClient | None = None):
        """Initialize the podcast service.

        Args:
            itunes_client: iTunes API client (creates default if not provided)
        """
        self.itunes_client = itunes_client or iTunesClient()
        self._episode_cache: dict[str, list[Episode]] = {}

    def search(self, term: str, limit: int = 10) -> list[Podcast]:
        """Search for podcasts matching the given term.

        Args:
            term: Search term
            limit: Maximum number of results

        Returns:
            List of matching Podcast objects
        """
        return self.itunes_client.search_podcasts(term, limit)

    def get_episodes(self, feed_url: str, limit: int = 10) -> list[Episode]:
        """Get episodes from a podcast feed.

        Args:
            feed_url: RSS feed URL
            limit: Maximum number of episodes to return

        Returns:
            List of Episode objects (most recent first)

        Raises:
            PodcastError: If feed cannot be parsed
        """
        try:
            feed = self._fetch_feed(feed_url)
        except Exception as e:
            raise PodcastError(f"Failed to fetch feed: {e}") from e

        episodes = self._parse_episodes(feed)

        # Cache for later retrieval by index
        self._episode_cache[feed_url] = episodes

        # Return limited results
        return episodes[:limit]

    def get_episode_by_index(self, feed_url: str, index: int, limit: int = 10) -> Episode:
        """Get a specific episode by its display index.

        Args:
            feed_url: RSS feed URL
            index: 1-based index from the displayed list
            limit: The limit used when displaying episodes

        Returns:
            The Episode at the specified index

        Raises:
            PodcastError: If index is out of range
        """
        # Ensure we have the episodes cached
        if feed_url not in self._episode_cache:
            self.get_episodes(feed_url, limit)

        episodes = self._episode_cache.get(feed_url, [])[:limit]

        if index < 1 or index > len(episodes):
            raise PodcastError(f"Episode index {index} out of range (1-{len(episodes)})")

        return episodes[index - 1]

    def _fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Fetch and parse an RSS feed."""
        # Use httpx for better error handling
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.text

        feed = feedparser.parse(content)

        if feed.bozo and not feed.entries:
            raise PodcastError(f"Invalid feed format: {feed.bozo_exception}")

        return feed

    def _parse_episodes(self, feed: feedparser.FeedParserDict) -> list[Episode]:
        """Parse episodes from a feed."""
        episodes = []

        for entry in feed.entries:
            episode = self._parse_entry(entry, feed)
            if episode:
                episodes.append(episode)

        # Sort by publication date (most recent first)
        episodes.sort(key=lambda e: e.pub_date, reverse=True)

        return episodes

    def _parse_entry(
        self, entry: feedparser.FeedParserDict, feed: feedparser.FeedParserDict
    ) -> Episode | None:
        """Parse a single feed entry into an Episode."""
        # Get title
        title = entry.get("title", "Untitled")

        # Get publication date
        pub_date = self._parse_date(entry)
        if pub_date is None:
            pub_date = datetime.now()

        # Get media URL from enclosures
        media_url = self._get_media_url(entry)
        if not media_url:
            return None

        # Get duration
        duration = self._parse_duration(entry)

        # Get language from feed
        language = feed.feed.get("language", "en")
        if language:
            language = language.split("-")[0].lower()

        return Episode(
            title=title,
            pub_date=pub_date,
            media_url=media_url,
            duration=duration,
            description=entry.get("summary", ""),
            guid=entry.get("id", ""),
            language=language,
        )

    def _parse_date(self, entry: feedparser.FeedParserDict) -> datetime | None:
        """Parse publication date from entry."""
        # Try parsed date first
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Try string parsing
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                return parsedate_to_datetime(date_str)
            except (TypeError, ValueError):
                pass

        return None

    def _get_media_url(self, entry: feedparser.FeedParserDict) -> str | None:
        """Extract media URL from entry enclosures."""
        # Check enclosures
        for enclosure in entry.get("enclosures", []):
            url = enclosure.get("href") or enclosure.get("url")
            if url:
                media_type = enclosure.get("type", "")
                if media_type.startswith(("audio/", "video/")):
                    return url
                # Accept URL even without type if it looks like media
                if any(ext in url.lower() for ext in [".mp3", ".m4a", ".mp4", ".wav"]):
                    return url

        # Check media:content
        for media in entry.get("media_content", []):
            url = media.get("url")
            if url:
                return url

        # Check links
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure":
                return link.get("href")

        return None

    def _parse_duration(self, entry: feedparser.FeedParserDict) -> int | None:
        """Parse duration in seconds from entry."""
        # Check itunes:duration
        duration_str = entry.get("itunes_duration")
        if not duration_str:
            return None

        # Handle different formats: "HH:MM:SS", "MM:SS", or just seconds
        duration_str = str(duration_str).strip()

        # If it's just a number, assume seconds
        if duration_str.isdigit():
            return int(duration_str)

        # Parse time format
        parts = duration_str.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            pass

        return None

    def get_podcast_name(self, feed_url: str) -> str:
        """Get the podcast name from a feed URL.

        Args:
            feed_url: RSS feed URL

        Returns:
            Podcast title or sanitized URL if unavailable
        """
        try:
            feed = self._fetch_feed(feed_url)
            return feed.feed.get("title", self._sanitize_name(feed_url))
        except Exception:
            return self._sanitize_name(feed_url)

    def _sanitize_name(self, text: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove protocol and common domains
        text = re.sub(r"https?://", "", text)
        text = re.sub(r"www\.", "", text)
        # Replace invalid characters
        text = re.sub(r'[<>:"/\\|?*]', "_", text)
        # Limit length
        return text[:50]
