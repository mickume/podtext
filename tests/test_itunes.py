"""Tests for iTunes client."""

import pytest
import httpx
import respx

from podtext.clients.itunes import iTunesClient, iTunesError, ITUNES_SEARCH_URL


class TestiTunesClient:
    """Tests for iTunesClient."""

    @respx.mock
    def test_search_podcasts_success(self):
        """Test successful podcast search."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "Tech Talk",
                    "feedUrl": "https://example.com/tech.xml",
                    "artistName": "Tech Media",
                    "primaryGenreName": "Technology",
                },
                {
                    "collectionName": "Science Hour",
                    "feedUrl": "https://example.com/science.xml",
                    "artistName": "Science Network",
                    "primaryGenreName": "Science",
                },
            ],
        }

        respx.get(ITUNES_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = iTunesClient()
        results = client.search_podcasts("tech", limit=10)

        assert len(results) == 2
        assert results[0].title == "Tech Talk"
        assert results[0].feed_url == "https://example.com/tech.xml"
        assert results[0].author == "Tech Media"
        assert results[0].genre == "Technology"

    @respx.mock
    def test_search_podcasts_empty_results(self):
        """Test search with no results."""
        mock_response = {"resultCount": 0, "results": []}

        respx.get(ITUNES_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = iTunesClient()
        results = client.search_podcasts("nonexistent", limit=10)

        assert len(results) == 0

    @respx.mock
    def test_search_podcasts_skips_no_feed_url(self):
        """Test that results without feed URL are skipped."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "No Feed",
                    "artistName": "Author",
                    # No feedUrl
                },
                {
                    "collectionName": "Has Feed",
                    "feedUrl": "https://example.com/feed.xml",
                    "artistName": "Author",
                },
            ],
        }

        respx.get(ITUNES_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = iTunesClient()
        results = client.search_podcasts("test", limit=10)

        assert len(results) == 1
        assert results[0].title == "Has Feed"

    @respx.mock
    def test_search_podcasts_http_error(self):
        """Test handling of HTTP errors."""
        respx.get(ITUNES_SEARCH_URL).mock(
            return_value=httpx.Response(500, text="Server Error")
        )

        client = iTunesClient()

        with pytest.raises(iTunesError) as exc_info:
            client.search_podcasts("test")

        assert "500" in str(exc_info.value)

    @respx.mock
    def test_search_podcasts_timeout(self):
        """Test handling of timeout errors."""
        respx.get(ITUNES_SEARCH_URL).mock(side_effect=httpx.TimeoutException("timeout"))

        client = iTunesClient()

        with pytest.raises(iTunesError) as exc_info:
            client.search_podcasts("test")

        assert "timed out" in str(exc_info.value).lower()

    @respx.mock
    def test_search_podcasts_request_error(self):
        """Test handling of request errors."""
        respx.get(ITUNES_SEARCH_URL).mock(
            side_effect=httpx.RequestError("connection failed")
        )

        client = iTunesClient()

        with pytest.raises(iTunesError) as exc_info:
            client.search_podcasts("test")

        assert "failed" in str(exc_info.value).lower()

    @respx.mock
    def test_search_respects_limit(self):
        """Test that limit parameter is passed to API."""
        mock_response = {"resultCount": 0, "results": []}

        route = respx.get(ITUNES_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = iTunesClient()
        client.search_podcasts("test", limit=25)

        assert route.called
        request = route.calls[0].request
        assert "limit=25" in str(request.url)
