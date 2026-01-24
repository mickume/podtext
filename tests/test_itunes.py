"""Unit tests for the iTunes API client.

Tests podcast search functionality, JSON parsing, and error handling.

Requirements: 1.1, 1.5
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from podtext.services.itunes import (
    ITunesAPIError,
    PodcastSearchResult,
    _parse_search_results,
    search_podcasts,
)


class TestPodcastSearchResult:
    """Tests for PodcastSearchResult dataclass."""

    def test_create_search_result(self) -> None:
        """Test creating a PodcastSearchResult."""
        result = PodcastSearchResult(
            title="Test Podcast",
            feed_url="https://example.com/feed.xml",
        )

        assert result.title == "Test Podcast"
        assert result.feed_url == "https://example.com/feed.xml"

    def test_search_result_equality(self) -> None:
        """Test that two identical results are equal."""
        result1 = PodcastSearchResult(
            title="Test Podcast",
            feed_url="https://example.com/feed.xml",
        )
        result2 = PodcastSearchResult(
            title="Test Podcast",
            feed_url="https://example.com/feed.xml",
        )

        assert result1 == result2


class TestParseSearchResults:
    """Tests for _parse_search_results function."""

    def test_parse_empty_results(self) -> None:
        """Test parsing empty results."""
        data: dict[str, Any] = {"resultCount": 0, "results": []}
        results = _parse_search_results(data)

        assert results == []

    def test_parse_single_result(self) -> None:
        """Test parsing a single podcast result."""
        data: dict[str, Any] = {
            "resultCount": 1,
            "results": [
                {
                    "collectionName": "Test Podcast",
                    "feedUrl": "https://example.com/feed.xml",
                    "artistName": "Test Artist",
                }
            ],
        }
        results = _parse_search_results(data)

        assert len(results) == 1
        assert results[0].title == "Test Podcast"
        assert results[0].feed_url == "https://example.com/feed.xml"

    def test_parse_multiple_results(self) -> None:
        """Test parsing multiple podcast results."""
        data: dict[str, Any] = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "Podcast One",
                    "feedUrl": "https://example.com/feed1.xml",
                },
                {
                    "collectionName": "Podcast Two",
                    "feedUrl": "https://example.com/feed2.xml",
                },
            ],
        }
        results = _parse_search_results(data)

        assert len(results) == 2
        assert results[0].title == "Podcast One"
        assert results[1].title == "Podcast Two"

    def test_parse_result_with_trackname_fallback(self) -> None:
        """Test parsing result that uses trackName instead of collectionName."""
        data: dict[str, Any] = {
            "resultCount": 1,
            "results": [
                {
                    "trackName": "Track Name Podcast",
                    "feedUrl": "https://example.com/feed.xml",
                }
            ],
        }
        results = _parse_search_results(data)

        assert len(results) == 1
        assert results[0].title == "Track Name Podcast"

    def test_parse_skips_results_without_feed_url(self) -> None:
        """Test that results without feedUrl are skipped."""
        data: dict[str, Any] = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "Podcast With Feed",
                    "feedUrl": "https://example.com/feed.xml",
                },
                {
                    "collectionName": "Podcast Without Feed",
                    # No feedUrl
                },
            ],
        }
        results = _parse_search_results(data)

        assert len(results) == 1
        assert results[0].title == "Podcast With Feed"

    def test_parse_skips_results_without_title(self) -> None:
        """Test that results without title are skipped."""
        data: dict[str, Any] = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "Podcast With Title",
                    "feedUrl": "https://example.com/feed1.xml",
                },
                {
                    # No title
                    "feedUrl": "https://example.com/feed2.xml",
                },
            ],
        }
        results = _parse_search_results(data)

        assert len(results) == 1
        assert results[0].title == "Podcast With Title"

    def test_parse_missing_results_key(self) -> None:
        """Test parsing data without results key."""
        data: dict[str, Any] = {"resultCount": 0}
        results = _parse_search_results(data)

        assert results == []


class TestSearchPodcasts:
    """Tests for search_podcasts function.
    
    Validates: Requirements 1.1, 1.5
    """

    def test_search_empty_query(self) -> None:
        """Test that empty query returns empty results."""
        results = search_podcasts("")
        assert results == []

    def test_search_whitespace_query(self) -> None:
        """Test that whitespace-only query returns empty results."""
        results = search_podcasts("   ")
        assert results == []

    def test_search_zero_limit(self) -> None:
        """Test that zero limit returns empty results."""
        results = search_podcasts("python", limit=0)
        assert results == []

    def test_search_negative_limit(self) -> None:
        """Test that negative limit returns empty results."""
        results = search_podcasts("python", limit=-5)
        assert results == []

    @patch("podtext.services.itunes.httpx.Client")
    def test_search_successful(self, mock_client_class: MagicMock) -> None:
        """Test successful podcast search.
        
        Validates: Requirement 1.1
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "resultCount": 2,
            "results": [
                {
                    "collectionName": "Python Podcast",
                    "feedUrl": "https://example.com/python.xml",
                },
                {
                    "collectionName": "Coding Show",
                    "feedUrl": "https://example.com/coding.xml",
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        results = search_podcasts("python", limit=10)

        assert len(results) == 2
        assert results[0].title == "Python Podcast"
        assert results[0].feed_url == "https://example.com/python.xml"
        assert results[1].title == "Coding Show"

        # Verify API was called with correct parameters
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == "https://itunes.apple.com/search"
        assert call_args[1]["params"]["term"] == "python"
        assert call_args[1]["params"]["media"] == "podcast"
        assert call_args[1]["params"]["limit"] == 10

    @patch("podtext.services.itunes.httpx.Client")
    def test_search_with_custom_limit(self, mock_client_class: MagicMock) -> None:
        """Test search with custom limit parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"resultCount": 0, "results": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        search_podcasts("test", limit=5)

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["limit"] == 5

    @patch("podtext.services.itunes.httpx.Client")
    def test_search_strips_query_whitespace(self, mock_client_class: MagicMock) -> None:
        """Test that query whitespace is stripped."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"resultCount": 0, "results": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        search_podcasts("  python programming  ", limit=10)

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["term"] == "python programming"


class TestSearchPodcastsErrorHandling:
    """Tests for error handling in search_podcasts.
    
    Validates: Requirement 1.5
    """

    @patch("podtext.services.itunes.httpx.Client")
    def test_timeout_error(self, mock_client_class: MagicMock) -> None:
        """Test that timeout raises ITunesAPIError.
        
        Validates: Requirement 1.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(ITunesAPIError) as exc_info:
            search_podcasts("python")

        assert "timed out" in str(exc_info.value).lower()

    @patch("podtext.services.itunes.httpx.Client")
    def test_http_status_error(self, mock_client_class: MagicMock) -> None:
        """Test that HTTP error status raises ITunesAPIError.
        
        Validates: Requirement 1.5
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(ITunesAPIError) as exc_info:
            search_podcasts("python")

        assert "500" in str(exc_info.value)

    @patch("podtext.services.itunes.httpx.Client")
    def test_connection_error(self, mock_client_class: MagicMock) -> None:
        """Test that connection error raises ITunesAPIError.
        
        Validates: Requirement 1.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(ITunesAPIError) as exc_info:
            search_podcasts("python")

        assert "Failed to connect" in str(exc_info.value)

    @patch("podtext.services.itunes.httpx.Client")
    def test_invalid_json_response(self, mock_client_class: MagicMock) -> None:
        """Test that invalid JSON response raises ITunesAPIError.
        
        Validates: Requirement 1.5
        """
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(ITunesAPIError) as exc_info:
            search_podcasts("python")

        assert "invalid json" in str(exc_info.value).lower()

    @patch("podtext.services.itunes.httpx.Client")
    def test_request_error(self, mock_client_class: MagicMock) -> None:
        """Test that generic request error raises ITunesAPIError.
        
        Validates: Requirement 1.5
        """
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("Network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(ITunesAPIError) as exc_info:
            search_podcasts("python")

        assert "Failed to connect" in str(exc_info.value)
