"""iTunes API client for podcast search.

Uses Apple's iTunes Search API to find podcasts by keywords.
"""

import httpx

from .models import PodcastSearchResult


ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


class ITunesAPIError(Exception):
    """Error from iTunes API."""

    pass


def search_podcasts(query: str, limit: int = 10) -> list[PodcastSearchResult]:
    """Search for podcasts using iTunes API.

    Args:
        query: Search keywords.
        limit: Maximum number of results to return (default 10).

    Returns:
        List of PodcastSearchResult objects.

    Raises:
        ITunesAPIError: If the API request fails.
    """
    if limit <= 0:
        return []

    params = {
        "term": query,
        "media": "podcast",
        "entity": "podcast",
        "limit": limit,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(ITUNES_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise ITunesAPIError(f"iTunes API returned error: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ITunesAPIError(f"Failed to connect to iTunes API: {e}") from e
    except ValueError as e:
        raise ITunesAPIError(f"Invalid JSON response from iTunes API: {e}") from e

    results = []
    for item in data.get("results", []):
        # Only include results with both title and feed URL
        title = item.get("collectionName") or item.get("trackName")
        feed_url = item.get("feedUrl")

        if title and feed_url:
            results.append(PodcastSearchResult(title=title, feed_url=feed_url))

    # Ensure we don't exceed the limit
    return results[:limit]
