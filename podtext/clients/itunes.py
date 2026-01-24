"""iTunes Search API client."""

import httpx

from podtext.models.podcast import Podcast

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
DEFAULT_TIMEOUT = 30.0


class iTunesError(Exception):
    """Exception raised for iTunes API errors."""

    pass


class iTunesClient:
    """Client for the iTunes Search API."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the iTunes client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def search_podcasts(self, term: str, limit: int = 10) -> list[Podcast]:
        """Search for podcasts matching the given term.

        Args:
            term: Search term (title, author, keywords)
            limit: Maximum number of results to return

        Returns:
            List of matching Podcast objects

        Raises:
            iTunesError: If the API request fails
        """
        params = {
            "term": term,
            "media": "podcast",
            "entity": "podcast",
            "limit": limit,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(ITUNES_SEARCH_URL, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise iTunesError(f"Request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            raise iTunesError(f"HTTP error {e.response.status_code}: {e}") from e
        except httpx.RequestError as e:
            raise iTunesError(f"Request failed: {e}") from e

        data = response.json()
        return self._parse_results(data)

    def _parse_results(self, data: dict) -> list[Podcast]:
        """Parse iTunes API response into Podcast objects."""
        podcasts = []

        for result in data.get("results", []):
            # Skip results without feed URL
            feed_url = result.get("feedUrl")
            if not feed_url:
                continue

            podcast = Podcast(
                title=result.get("collectionName", "Unknown"),
                feed_url=feed_url,
                author=result.get("artistName", ""),
                artwork_url=result.get("artworkUrl600", result.get("artworkUrl100", "")),
                genre=result.get("primaryGenreName", ""),
            )
            podcasts.append(podcast)

        return podcasts
