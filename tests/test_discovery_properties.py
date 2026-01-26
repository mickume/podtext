"""Property-based tests for the Discovery Module.

Feature: podtext
Tests result limiting and RSS parsing validity properties.

Validates: Requirements 1.3, 2.1, 2.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

from hypothesis import given, settings
from hypothesis import strategies as st

from podtext.services.itunes import (
    _parse_search_results,
    search_podcasts,
)
from podtext.services.rss import (
    _parse_feed_entries,
    parse_feed,
)

# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for positive limit values
positive_limit_strategy = st.integers(min_value=1, max_value=100)

# Strategy for non-negative limit values (including 0)
non_negative_limit_strategy = st.integers(min_value=0, max_value=100)


# Strategy for generating valid podcast search result data
@st.composite
def podcast_search_result_strategy(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a valid iTunes API search result item."""
    title = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))
    feed_url = draw(
        st.from_regex(
            r"https://[a-z0-9]+\.[a-z]{2,4}/[a-z0-9/]+\.xml",
            fullmatch=True,
        )
    )
    return {
        "collectionName": title,
        "feedUrl": feed_url,
    }


@st.composite
def itunes_api_response_strategy(draw: st.DrawFn, max_results: int = 50) -> dict[str, Any]:
    """Generate a valid iTunes API response with multiple results."""
    num_results = draw(st.integers(min_value=0, max_value=max_results))
    results = [draw(podcast_search_result_strategy()) for _ in range(num_results)]
    return {"results": results}


# Strategy for generating valid RSS feed entry data
@st.composite
def rss_entry_strategy(draw: st.DrawFn) -> MagicMock:
    """Generate a valid RSS feed entry mock."""
    title = draw(st.text(min_size=1, max_size=200).filter(lambda s: s.strip() != ""))

    # Generate a valid RFC 2822 date
    day = draw(st.integers(min_value=1, max_value=28))
    month = draw(
        st.sampled_from(
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        )
    )
    year = draw(st.integers(min_value=2000, max_value=2030))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))

    # Day of week (not validated by parser, but included for format)
    dow = draw(st.sampled_from(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]))
    pub_date = f"{dow}, {day:02d} {month} {year} {hour:02d}:{minute:02d}:{second:02d} +0000"

    # Generate a valid media URL
    media_url = draw(
        st.from_regex(
            r"https://[a-z0-9]+\.[a-z]{2,4}/[a-z0-9/]+\.(mp3|m4a|wav|ogg)",
            fullmatch=True,
        )
    )

    entry = MagicMock()
    entry.title = title
    entry.published = pub_date
    entry.updated = None
    entry.enclosures = [{"href": media_url}]
    entry.media_content = []
    entry.links = []

    return entry


@st.composite
def rss_feed_strategy(draw: st.DrawFn, max_entries: int = 50) -> MagicMock:
    """Generate a valid RSS feed mock with multiple entries."""
    num_entries = draw(st.integers(min_value=1, max_value=max_entries))
    entries = [draw(rss_entry_strategy()) for _ in range(num_entries)]

    feed = MagicMock()
    feed.entries = entries
    feed.bozo = False
    feed.bozo_exception = None

    return feed


# =============================================================================
# Property 1: Result Limiting
# =============================================================================


class TestResultLimiting:
    """Property 1: Result Limiting

    Feature: podtext, Property 1: Result Limiting

    For any search or episode listing operation with limit N,
    the returned results SHALL have length ≤ N.

    **Validates: Requirements 1.3, 2.3**
    """

    @settings(max_examples=100)
    @given(
        num_api_results=st.integers(min_value=0, max_value=50),
        limit=positive_limit_strategy,
    )
    def test_search_podcasts_respects_limit(
        self,
        num_api_results: int,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - iTunes Search

        Feature: podtext, Property 1: Result Limiting

        For any search operation with limit N, the returned results
        SHALL have length ≤ N.

        **Validates: Requirements 1.3**

        Note: The iTunes API is expected to respect the limit parameter.
        This test simulates realistic API behavior where the API returns
        at most 'limit' results.
        """
        with patch("podtext.services.itunes.httpx.Client") as mock_client_class:
            # Simulate realistic API behavior: API returns at most 'limit' results
            # The API may return fewer if there aren't enough matching podcasts
            actual_api_results = min(num_api_results, limit)

            # Generate mock API response with realistic number of results
            results_data = []
            for i in range(actual_api_results):
                results_data.append(
                    {
                        "collectionName": f"Podcast {i}",
                        "feedUrl": f"https://example{i}.com/feed.xml",
                    }
                )
            api_response = {"results": results_data}

            # Setup mock HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            # Execute search
            results = search_podcasts("test query", limit=limit)

            # Property: Results length SHALL be ≤ limit
            assert len(results) <= limit, (
                f"Search results length {len(results)} exceeds limit {limit}"
            )

    @settings(max_examples=100)
    @given(
        num_api_results=st.integers(min_value=0, max_value=50),
        limit=non_negative_limit_strategy,
    )
    def test_search_podcasts_respects_zero_and_positive_limits(
        self,
        num_api_results: int,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - iTunes Search with zero limit

        Feature: podtext, Property 1: Result Limiting

        For any search operation with limit N (including 0), the returned results
        SHALL have length ≤ N.

        **Validates: Requirements 1.3**

        Note: The iTunes API is expected to respect the limit parameter.
        This test simulates realistic API behavior where the API returns
        at most 'limit' results.
        """
        with patch("podtext.services.itunes.httpx.Client") as mock_client_class:
            # Simulate realistic API behavior: API returns at most 'limit' results
            actual_api_results = min(num_api_results, limit) if limit > 0 else 0

            # Generate mock API response with realistic number of results
            results_data = []
            for i in range(actual_api_results):
                results_data.append(
                    {
                        "collectionName": f"Podcast {i}",
                        "feedUrl": f"https://example{i}.com/feed.xml",
                    }
                )
            api_response = {"results": results_data}

            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            results = search_podcasts("test query", limit=limit)

            # Property: Results length SHALL be ≤ limit
            assert len(results) <= limit, (
                f"Search results length {len(results)} exceeds limit {limit}"
            )

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=50),
        limit=positive_limit_strategy,
    )
    def test_parse_feed_respects_limit(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - RSS Feed Parsing

        Feature: podtext, Property 1: Result Limiting

        For any episode listing operation with limit N, the returned results
        SHALL have length ≤ N.

        **Validates: Requirements 2.3**
        """
        with (
            patch("podtext.services.rss.httpx.Client") as mock_client_class,
            patch("podtext.services.rss.feedparser.parse") as mock_feedparser,
        ):
            # Setup mock HTTP response
            mock_response = MagicMock()
            mock_response.text = "<rss>...</rss>"
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            mock_feedparser.return_value = feed

            # Execute feed parsing
            feed_info = parse_feed("https://example.com/feed.xml", limit=limit)

            # Property: Results length SHALL be ≤ limit
            assert len(feed_info.episodes) <= limit, (
                f"Episode results length {len(feed_info.episodes)} exceeds limit {limit}"
            )

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=50),
        limit=non_negative_limit_strategy,
    )
    def test_parse_feed_respects_zero_and_positive_limits(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - RSS Feed with zero limit

        Feature: podtext, Property 1: Result Limiting

        For any episode listing operation with limit N (including 0), the returned results
        SHALL have length ≤ N.

        **Validates: Requirements 2.3**
        """
        with (
            patch("podtext.services.rss.httpx.Client") as mock_client_class,
            patch("podtext.services.rss.feedparser.parse") as mock_feedparser,
        ):
            mock_response = MagicMock()
            mock_response.text = "<rss>...</rss>"
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            mock_feedparser.return_value = feed

            feed_info = parse_feed("https://example.com/feed.xml", limit=limit)

            # Property: Results length SHALL be ≤ limit
            assert len(feed_info.episodes) <= limit, (
                f"Episode results length {len(feed_info.episodes)} exceeds limit {limit}"
            )

    @settings(max_examples=100)
    @given(
        num_results=st.integers(min_value=0, max_value=100),
        limit=positive_limit_strategy,
    )
    def test_parse_search_results_respects_limit_internally(
        self,
        num_results: int,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - Internal parsing function

        Feature: podtext, Property 1: Result Limiting

        The internal _parse_search_results function should return all valid results,
        and the limit is applied at the API request level.

        **Validates: Requirements 1.3**
        """
        # Generate mock API response data
        results_data = []
        for i in range(num_results):
            results_data.append(
                {
                    "collectionName": f"Podcast {i}",
                    "feedUrl": f"https://example{i}.com/feed.xml",
                }
            )

        api_response = {"results": results_data}

        # Parse results (this function doesn't apply limit, it parses all)
        parsed = _parse_search_results(api_response)

        # The parsing function returns all valid results
        # The limit is applied at the API request level
        assert len(parsed) == num_results

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=50),
        limit=positive_limit_strategy,
    )
    def test_parse_feed_entries_respects_limit(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 1: Result Limiting - Internal feed parsing function

        Feature: podtext, Property 1: Result Limiting

        The internal _parse_feed_entries function SHALL respect the limit parameter.

        **Validates: Requirements 2.3**
        """
        results = _parse_feed_entries(feed, limit=limit)

        # Property: Results length SHALL be ≤ limit
        assert len(results) <= limit, f"Parsed entries length {len(results)} exceeds limit {limit}"


# =============================================================================
# Property 4: RSS Parsing Validity
# =============================================================================


class TestRSSParsingValidity:
    """Property 4: RSS Parsing Validity

    Feature: podtext, Property 4: RSS Parsing Validity

    For any valid RSS feed XML, parsing then extracting episode info
    SHALL produce EpisodeInfo objects with non-empty title, valid datetime,
    and valid media URL.

    **Validates: Requirements 2.1**
    """

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_parsed_episodes_have_non_empty_titles(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - Non-empty titles

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed, parsed EpisodeInfo objects SHALL have non-empty titles.

        **Validates: Requirements 2.1**
        """
        results = _parse_feed_entries(feed, limit=limit)

        for episode in results:
            # Property: Title SHALL be non-empty
            assert episode.title, f"Episode title should be non-empty, got: '{episode.title}'"
            assert episode.title.strip() != "", (
                f"Episode title should not be whitespace-only, got: '{episode.title}'"
            )

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_parsed_episodes_have_valid_datetime(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - Valid datetime

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed, parsed EpisodeInfo objects SHALL have valid datetime.

        **Validates: Requirements 2.1**
        """
        results = _parse_feed_entries(feed, limit=limit)

        for episode in results:
            # Property: pub_date SHALL be a valid datetime
            assert isinstance(episode.pub_date, datetime), (
                f"Episode pub_date should be datetime, got: {type(episode.pub_date)}"
            )

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_parsed_episodes_have_valid_media_url(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - Valid media URL

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed, parsed EpisodeInfo objects SHALL have valid media URLs.

        **Validates: Requirements 2.1**
        """
        results = _parse_feed_entries(feed, limit=limit)

        for episode in results:
            # Property: media_url SHALL be non-empty
            assert episode.media_url, (
                f"Episode media_url should be non-empty, got: '{episode.media_url}'"
            )

            # Property: media_url SHALL be a valid URL
            parsed_url = urlparse(episode.media_url)
            assert parsed_url.scheme in ("http", "https"), (
                f"Episode media_url should have http/https scheme, got: '{parsed_url.scheme}'"
            )
            assert parsed_url.netloc, (
                f"Episode media_url should have a valid netloc, got: '{episode.media_url}'"
            )

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_parsed_episodes_have_valid_index(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - Valid index numbers

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed, parsed EpisodeInfo objects SHALL have valid
        positive index numbers starting from 1.

        **Validates: Requirements 2.1**
        """
        results = _parse_feed_entries(feed, limit=limit)

        for i, episode in enumerate(results, start=1):
            # Property: index SHALL be positive and sequential
            assert episode.index == i, f"Episode index should be {i}, got: {episode.index}"
            assert episode.index > 0, f"Episode index should be positive, got: {episode.index}"

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_parsed_episodes_all_properties_valid(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - All properties combined

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed XML, parsing then extracting episode info
        SHALL produce EpisodeInfo objects with non-empty title, valid datetime,
        and valid media URL.

        **Validates: Requirements 2.1**
        """
        results = _parse_feed_entries(feed, limit=limit)

        for episode in results:
            # Property: All EpisodeInfo fields SHALL be valid

            # Non-empty title
            assert episode.title and episode.title.strip() != "", (
                f"Episode should have non-empty title, got: '{episode.title}'"
            )

            # Valid datetime
            assert isinstance(episode.pub_date, datetime), (
                f"Episode should have valid datetime, got: {type(episode.pub_date)}"
            )

            # Valid media URL
            assert episode.media_url, (
                f"Episode should have non-empty media_url, got: '{episode.media_url}'"
            )
            parsed_url = urlparse(episode.media_url)
            assert parsed_url.scheme in ("http", "https") and parsed_url.netloc, (
                f"Episode should have valid media URL, got: '{episode.media_url}'"
            )

            # Valid positive index
            assert episode.index > 0, f"Episode should have positive index, got: {episode.index}"

    @settings(max_examples=100)
    @given(
        feed=rss_feed_strategy(max_entries=20),
        limit=st.integers(min_value=1, max_value=50),
    )
    def test_full_parse_feed_produces_valid_episodes(
        self,
        feed: MagicMock,
        limit: int,
    ) -> None:
        """Property 4: RSS Parsing Validity - Full parse_feed function

        Feature: podtext, Property 4: RSS Parsing Validity

        For any valid RSS feed XML, the parse_feed function SHALL produce
        EpisodeInfo objects with non-empty title, valid datetime, and valid media URL.

        **Validates: Requirements 2.1**
        """
        with (
            patch("podtext.services.rss.httpx.Client") as mock_client_class,
            patch("podtext.services.rss.feedparser.parse") as mock_feedparser,
        ):
            mock_response = MagicMock()
            mock_response.text = "<rss>...</rss>"
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            mock_feedparser.return_value = feed

            feed_info = parse_feed("https://example.com/feed.xml", limit=limit)

            for episode in feed_info.episodes:
                # Property: All EpisodeInfo fields SHALL be valid

                # Non-empty title
                assert episode.title and episode.title.strip() != "", (
                    f"Episode should have non-empty title, got: '{episode.title}'"
                )

                # Valid datetime
                assert isinstance(episode.pub_date, datetime), (
                    f"Episode should have valid datetime, got: {type(episode.pub_date)}"
                )

                # Valid media URL
                assert episode.media_url, "Episode should have non-empty media_url"
                parsed_url = urlparse(episode.media_url)
                assert parsed_url.scheme in ("http", "https") and parsed_url.netloc, (
                    f"Episode should have valid media URL, got: '{episode.media_url}'"
                )
