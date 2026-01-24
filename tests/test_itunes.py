"""Tests for iTunes API client.

Feature: podtext
Property 1: Result Limiting (for search)
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import respx
from httpx import Response

from podtext.itunes import search_podcasts, ITunesAPIError, ITUNES_SEARCH_URL
from podtext.models import PodcastSearchResult


class TestSearchBasics:
    """Basic search functionality tests."""

    @respx.mock
    def test_search_returns_results(self):
        """Test that search returns PodcastSearchResult objects."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {"collectionName": "Podcast One", "feedUrl": "https://feed1.com/rss"},
                {"collectionName": "Podcast Two", "feedUrl": "https://feed2.com/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test")

        assert len(results) == 2
        assert all(isinstance(r, PodcastSearchResult) for r in results)
        assert results[0].title == "Podcast One"
        assert results[0].feed_url == "https://feed1.com/rss"

    @respx.mock
    def test_search_skips_results_without_feed_url(self):
        """Test that results without feedUrl are skipped."""
        mock_response = {
            "resultCount": 2,
            "results": [
                {"collectionName": "Has Feed", "feedUrl": "https://feed.com/rss"},
                {"collectionName": "No Feed"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test")

        assert len(results) == 1
        assert results[0].title == "Has Feed"

    @respx.mock
    def test_search_uses_trackname_fallback(self):
        """Test that trackName is used if collectionName is missing."""
        mock_response = {
            "resultCount": 1,
            "results": [
                {"trackName": "Track Name", "feedUrl": "https://feed.com/rss"},
            ]
        }
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test")

        assert results[0].title == "Track Name"

    @respx.mock
    def test_search_handles_empty_results(self):
        """Test that empty results are handled."""
        mock_response = {"resultCount": 0, "results": []}
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test")

        assert results == []

    @respx.mock
    def test_search_handles_api_error(self):
        """Test that API errors are properly raised."""
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(500))

        with pytest.raises(ITunesAPIError, match="iTunes API returned error"):
            search_podcasts("test")

    @respx.mock
    def test_search_handles_invalid_json(self):
        """Test that invalid JSON responses are handled."""
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, text="not json"))

        with pytest.raises(ITunesAPIError, match="Invalid JSON response"):
            search_podcasts("test")

    def test_search_with_zero_limit(self):
        """Test that zero limit returns empty list."""
        results = search_podcasts("test", limit=0)
        assert results == []

    def test_search_with_negative_limit(self):
        """Test that negative limit returns empty list."""
        results = search_podcasts("test", limit=-1)
        assert results == []


class TestProperty1ResultLimiting:
    """Property 1: Result Limiting.

    For any search operation with limit N, the returned results SHALL have length ≤ N.

    Validates: Requirements 1.3, 1.4
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        limit=st.integers(min_value=1, max_value=50),
        num_results=st.integers(min_value=0, max_value=100),
    )
    @respx.mock
    def test_search_respects_limit(self, limit, num_results):
        """Search results never exceed the specified limit."""
        # Generate mock response with num_results items
        results_data = [
            {"collectionName": f"Podcast {i}", "feedUrl": f"https://feed{i}.com/rss"}
            for i in range(num_results)
        ]
        mock_response = {"resultCount": num_results, "results": results_data}
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test", limit=limit)

        assert len(results) <= limit

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(limit=st.integers(min_value=1, max_value=20))
    @respx.mock
    def test_search_returns_exact_limit_when_available(self, limit):
        """When enough results are available, exactly limit results are returned."""
        # Generate more results than the limit
        results_data = [
            {"collectionName": f"Podcast {i}", "feedUrl": f"https://feed{i}.com/rss"}
            for i in range(limit + 10)
        ]
        mock_response = {"resultCount": limit + 10, "results": results_data}
        respx.get(ITUNES_SEARCH_URL).mock(return_value=Response(200, json=mock_response))

        results = search_podcasts("test", limit=limit)

        assert len(results) == limit
