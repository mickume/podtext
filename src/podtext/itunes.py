"""iTunes API client for podcast discovery."""

import httpx

from podtext.models import PodcastSearchResult


class ITunesAPIError(Exception):
    """Exception raised when iTunes API request fails."""

    pass


async def search_podcasts(
    query: str,
    limit: int = 10,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[PodcastSearchResult]:
    """
    Search for podcasts using the iTunes API.

    Args:
        query: Search keywords
        limit: Maximum number of results to return (default: 10)
        client: Optional httpx client for testing

    Returns:
        List of PodcastSearchResult objects

    Raises:
        ITunesAPIError: If the API request fails
    """
    if limit < 1:
        limit = 1

    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "media": "podcast",
        "entity": "podcast",
        "limit": limit,
    }

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        raise ITunesAPIError(f"iTunes API returned error status: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ITunesAPIError(f"Failed to connect to iTunes API: {e}") from e
    except ValueError as e:
        raise ITunesAPIError(f"Invalid JSON response from iTunes API: {e}") from e
    finally:
        if should_close_client:
            await client.aclose()

    results = []
    for item in data.get("results", []):
        # Extract feed URL - iTunes uses 'feedUrl' key
        feed_url = item.get("feedUrl")
        title = item.get("collectionName") or item.get("trackName", "Unknown")

        if feed_url:  # Only include results with valid feed URLs
            results.append(
                PodcastSearchResult(
                    title=title,
                    feed_url=feed_url,
                )
            )

    # Ensure we respect the limit
    return results[:limit]


def format_search_results(results: list[PodcastSearchResult]) -> str:
    """
    Format search results for display.

    Each result displays the title and feed URL.

    Args:
        results: List of podcast search results

    Returns:
        Formatted string for terminal display
    """
    if not results:
        return "No podcasts found."

    lines = []
    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   Feed: {result.feed_url}")
        lines.append("")

    return "\n".join(lines).rstrip()
