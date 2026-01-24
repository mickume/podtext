"""iTunes API client for podcast discovery.

Provides functionality to search for podcasts using Apple's iTunes Search API.

Requirements: 1.1, 1.5
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

# iTunes Search API endpoint
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

# Default timeout for API requests (in seconds)
DEFAULT_TIMEOUT = 30.0


class ITunesAPIError(Exception):
    """Raised when the iTunes API returns an error or is unreachable.
    
    Validates: Requirement 1.5
    """


@dataclass
class PodcastSearchResult:
    """Represents a podcast search result from iTunes.
    
    Attributes:
        title: The name of the podcast.
        feed_url: The RSS feed URL for the podcast.
    """
    
    title: str
    feed_url: str


def _parse_search_results(data: dict[str, Any]) -> list[PodcastSearchResult]:
    """Parse iTunes API JSON response into PodcastSearchResult objects.
    
    Args:
        data: The JSON response from iTunes API.
        
    Returns:
        List of PodcastSearchResult objects.
    """
    results: list[PodcastSearchResult] = []
    
    for item in data.get("results", []):
        # Only include results that have both required fields
        title = item.get("collectionName") or item.get("trackName")
        feed_url = item.get("feedUrl")
        
        if title and feed_url:
            results.append(
                PodcastSearchResult(
                    title=str(title),
                    feed_url=str(feed_url),
                )
            )
    
    return results


def search_podcasts(
    query: str,
    limit: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[PodcastSearchResult]:
    """Search for podcasts using the iTunes Search API.
    
    Queries the iTunes API with the provided search keywords and returns
    matching podcasts with their titles and feed URLs.
    
    Args:
        query: Search keywords to find podcasts.
        limit: Maximum number of results to return (default: 10).
        timeout: Request timeout in seconds (default: 30.0).
        
    Returns:
        List of PodcastSearchResult objects containing podcast title and feed URL.
        
    Raises:
        ITunesAPIError: If the API request fails or returns an error.
        
    Validates: Requirements 1.1, 1.5
    
    Example:
        >>> results = search_podcasts("python programming", limit=5)
        >>> for podcast in results:
        ...     print(f"{podcast.title}: {podcast.feed_url}")
    """
    if not query or not query.strip():
        return []
    
    # Ensure limit is positive
    if limit <= 0:
        return []
    
    params = {
        "term": query.strip(),
        "media": "podcast",
        "entity": "podcast",
        "limit": limit,
    }
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(ITUNES_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
    except httpx.TimeoutException as e:
        raise ITunesAPIError(
            f"iTunes API request timed out after {timeout} seconds"
        ) from e
        
    except httpx.HTTPStatusError as e:
        raise ITunesAPIError(
            f"iTunes API returned error status {e.response.status_code}: {e.response.text}"
        ) from e
        
    except httpx.RequestError as e:
        raise ITunesAPIError(
            f"Failed to connect to iTunes API: {e}"
        ) from e
        
    except ValueError as e:
        # JSON decode error
        raise ITunesAPIError(
            f"iTunes API returned invalid JSON response: {e}"
        ) from e
    
    return _parse_search_results(data)
