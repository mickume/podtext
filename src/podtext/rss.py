"""RSS feed parser for podcast episode discovery."""

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from podtext.models import EpisodeInfo


class RSSParseError(Exception):
    """Exception raised when RSS feed parsing fails."""

    pass


def _parse_pub_date(date_str: str | None) -> datetime:
    """Parse publication date from RSS feed."""
    if not date_str:
        return datetime.now()

    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return datetime.now()


def _extract_media_url(entry: dict) -> str | None:
    """Extract media URL from RSS entry."""
    # Try enclosures first (standard podcast format)
    enclosures = entry.get("enclosures", [])
    for enclosure in enclosures:
        href = enclosure.get("href") or enclosure.get("url")
        if href:
            media_type = enclosure.get("type", "")
            # Accept audio files
            if "audio" in media_type or href.endswith((".mp3", ".m4a", ".wav", ".ogg")):
                return href

    # Try media content
    media_content = entry.get("media_content", [])
    for media in media_content:
        url = media.get("url")
        if url:
            return url

    # Try links with audio type
    links = entry.get("links", [])
    for link in links:
        if link.get("type", "").startswith("audio/"):
            return link.get("href")

    # Last resort: check for any enclosure
    if enclosures:
        href = enclosures[0].get("href") or enclosures[0].get("url")
        if href:
            return href

    return None


async def parse_feed(
    feed_url: str,
    limit: int = 10,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[EpisodeInfo]:
    """
    Parse a podcast RSS feed and extract episode information.

    Args:
        feed_url: URL of the RSS feed
        limit: Maximum number of episodes to return (default: 10)
        client: Optional httpx client for testing

    Returns:
        List of EpisodeInfo objects for the most recent episodes

    Raises:
        RSSParseError: If the feed is invalid or unreachable
    """
    if limit < 1:
        limit = 1

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        response = await client.get(feed_url)
        response.raise_for_status()
        content = response.text
    except httpx.HTTPStatusError as e:
        raise RSSParseError(f"Failed to fetch RSS feed: HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise RSSParseError(f"Failed to connect to RSS feed: {e}") from e
    finally:
        if should_close_client:
            await client.aclose()

    # Parse the feed
    feed = feedparser.parse(content)

    if feed.bozo and not feed.entries:
        raise RSSParseError(f"Invalid RSS feed: {feed.bozo_exception}")

    # Get podcast title
    podcast_title = feed.feed.get("title", "Unknown Podcast")

    episodes = []
    for index, entry in enumerate(feed.entries[:limit], 1):
        title = entry.get("title", "Untitled Episode")
        pub_date = _parse_pub_date(entry.get("published"))
        media_url = _extract_media_url(entry)

        if media_url:  # Only include episodes with media
            episodes.append(
                EpisodeInfo(
                    index=index,
                    title=title,
                    pub_date=pub_date,
                    media_url=media_url,
                    podcast_title=podcast_title,
                )
            )

    return episodes[:limit]


def format_episodes(episodes: list[EpisodeInfo]) -> str:
    """
    Format episode list for display.

    Each episode displays the index, title, and publication date.

    Args:
        episodes: List of episode information

    Returns:
        Formatted string for terminal display
    """
    if not episodes:
        return "No episodes found."

    lines = []
    for episode in episodes:
        date_str = episode.pub_date.strftime("%Y-%m-%d")
        lines.append(f"{episode.index}. {episode.title}")
        lines.append(f"   Published: {date_str}")
        lines.append("")

    return "\n".join(lines).rstrip()


def get_episode_by_index(episodes: list[EpisodeInfo], index: int) -> EpisodeInfo | None:
    """
    Get an episode by its index number.

    Args:
        episodes: List of episodes
        index: The index number to find

    Returns:
        The matching EpisodeInfo or None if not found
    """
    for episode in episodes:
        if episode.index == index:
            return episode
    return None
