"""Property-based tests for CLI Display functions.

Feature: podtext
Tests search result display completeness and episode display completeness properties.

Validates: Requirements 1.2, 2.2
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from podtext.cli.main import format_episode_results, format_search_results
from podtext.services.itunes import PodcastSearchResult
from podtext.services.rss import EpisodeInfo

# =============================================================================
# Strategies for generating test data
# =============================================================================


@st.composite
def valid_title_strategy(draw: st.DrawFn) -> str:
    """Generate a valid non-empty title string."""
    # Generate printable text that is non-empty after stripping
    title = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N", "P", "S", "Zs"),
                blacklist_characters="\x00\n\r",
            ),
            min_size=1,
            max_size=200,
        )
    )
    # Ensure the title is non-empty after stripping
    assume(title.strip() != "")
    return title


@st.composite
def valid_feed_url_strategy(draw: st.DrawFn) -> str:
    """Generate a valid feed URL."""
    # Generate a valid URL pattern
    domain = draw(st.from_regex(r"[a-z][a-z0-9]{2,15}", fullmatch=True))
    tld = draw(st.sampled_from(["com", "org", "net", "io", "co"]))
    path = draw(st.from_regex(r"[a-z0-9]{1,20}", fullmatch=True))
    return f"https://{domain}.{tld}/{path}/feed.xml"


@st.composite
def podcast_search_result_strategy(draw: st.DrawFn) -> PodcastSearchResult:
    """Generate a valid PodcastSearchResult object."""
    title = draw(valid_title_strategy())
    feed_url = draw(valid_feed_url_strategy())
    return PodcastSearchResult(title=title, feed_url=feed_url)


@st.composite
def podcast_search_results_list_strategy(
    draw: st.DrawFn,
    min_size: int = 0,
    max_size: int = 20,
) -> list[PodcastSearchResult]:
    """Generate a list of PodcastSearchResult objects."""
    num_results = draw(st.integers(min_value=min_size, max_value=max_size))
    return [draw(podcast_search_result_strategy()) for _ in range(num_results)]


@st.composite
def valid_datetime_strategy(draw: st.DrawFn) -> datetime:
    """Generate a valid datetime for episode publication date."""
    year = draw(st.integers(min_value=2000, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


@st.composite
def valid_media_url_strategy(draw: st.DrawFn) -> str:
    """Generate a valid media URL."""
    domain = draw(st.from_regex(r"[a-z][a-z0-9]{2,15}", fullmatch=True))
    tld = draw(st.sampled_from(["com", "org", "net", "io"]))
    path = draw(st.from_regex(r"[a-z0-9]{1,20}", fullmatch=True))
    extension = draw(st.sampled_from(["mp3", "m4a", "wav", "ogg"]))
    return f"https://{domain}.{tld}/media/{path}.{extension}"


@st.composite
def episode_info_strategy(draw: st.DrawFn, index: int | None = None) -> EpisodeInfo:
    """Generate a valid EpisodeInfo object."""
    if index is None:
        index = draw(st.integers(min_value=1, max_value=1000))
    title = draw(valid_title_strategy())
    pub_date = draw(valid_datetime_strategy())
    media_url = draw(valid_media_url_strategy())
    return EpisodeInfo(
        index=index,
        title=title,
        pub_date=pub_date,
        media_url=media_url,
    )


@st.composite
def episode_info_list_strategy(
    draw: st.DrawFn,
    min_size: int = 0,
    max_size: int = 20,
) -> list[EpisodeInfo]:
    """Generate a list of EpisodeInfo objects with sequential indices."""
    num_episodes = draw(st.integers(min_value=min_size, max_value=max_size))
    episodes = []
    for i in range(1, num_episodes + 1):
        episode = draw(episode_info_strategy(index=i))
        episodes.append(episode)
    return episodes


# =============================================================================
# Property 2: Search Result Display Completeness
# =============================================================================


class TestSearchResultDisplayCompleteness:
    """Property 2: Search Result Display Completeness

    Feature: podtext, Property 2: Search Result Display Completeness

    For any list of PodcastSearchResult objects, the formatted display output
    SHALL contain both the title and feed_url for each result.

    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(results=podcast_search_results_list_strategy(min_size=0, max_size=20))
    def test_format_search_results_contains_all_titles(
        self,
        results: list[PodcastSearchResult],
    ) -> None:
        """Property 2: Search Result Display Completeness - Titles

        Feature: podtext, Property 2: Search Result Display Completeness

        For any list of PodcastSearchResult objects, the formatted display output
        SHALL contain the title for each result.

        **Validates: Requirements 1.2**
        """
        output = format_search_results(results)

        for result in results:
            # Property: Output SHALL contain the title for each result
            assert result.title in output, (
                f"Output should contain title '{result.title}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(results=podcast_search_results_list_strategy(min_size=0, max_size=20))
    def test_format_search_results_contains_all_feed_urls(
        self,
        results: list[PodcastSearchResult],
    ) -> None:
        """Property 2: Search Result Display Completeness - Feed URLs

        Feature: podtext, Property 2: Search Result Display Completeness

        For any list of PodcastSearchResult objects, the formatted display output
        SHALL contain the feed_url for each result.

        **Validates: Requirements 1.2**
        """
        output = format_search_results(results)

        for result in results:
            # Property: Output SHALL contain the feed_url for each result
            assert result.feed_url in output, (
                f"Output should contain feed_url '{result.feed_url}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(results=podcast_search_results_list_strategy(min_size=0, max_size=20))
    def test_format_search_results_contains_title_and_feed_url(
        self,
        results: list[PodcastSearchResult],
    ) -> None:
        """Property 2: Search Result Display Completeness - Combined

        Feature: podtext, Property 2: Search Result Display Completeness

        For any list of PodcastSearchResult objects, the formatted display output
        SHALL contain both the title and feed_url for each result.

        **Validates: Requirements 1.2**
        """
        output = format_search_results(results)

        for result in results:
            # Property: Output SHALL contain both title and feed_url for each result
            assert result.title in output, (
                f"Output should contain title '{result.title}', but it was not found.\n"
                f"Output:\n{output}"
            )
            assert result.feed_url in output, (
                f"Output should contain feed_url '{result.feed_url}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(results=podcast_search_results_list_strategy(min_size=1, max_size=20))
    def test_format_search_results_non_empty_list_produces_output(
        self,
        results: list[PodcastSearchResult],
    ) -> None:
        """Property 2: Search Result Display Completeness - Non-empty output

        Feature: podtext, Property 2: Search Result Display Completeness

        For any non-empty list of PodcastSearchResult objects, the formatted
        display output SHALL be non-empty and contain meaningful content.

        **Validates: Requirements 1.2**
        """
        output = format_search_results(results)

        # Property: Non-empty input SHALL produce non-empty output
        assert output, "Non-empty results list should produce non-empty output"
        assert output != "No podcasts found.", (
            "Non-empty results list should not produce 'No podcasts found.' message"
        )

    @settings(max_examples=100)
    @given(result=podcast_search_result_strategy())
    def test_format_search_results_single_result(
        self,
        result: PodcastSearchResult,
    ) -> None:
        """Property 2: Search Result Display Completeness - Single result

        Feature: podtext, Property 2: Search Result Display Completeness

        For a single PodcastSearchResult object, the formatted display output
        SHALL contain both the title and feed_url.

        **Validates: Requirements 1.2**
        """
        output = format_search_results([result])

        # Property: Output SHALL contain both title and feed_url
        assert result.title in output, (
            f"Output should contain title '{result.title}', but it was not found.\n"
            f"Output:\n{output}"
        )
        assert result.feed_url in output, (
            f"Output should contain feed_url '{result.feed_url}', but it was not found.\n"
            f"Output:\n{output}"
        )


# =============================================================================
# Property 3: Episode Display Completeness
# =============================================================================


class TestEpisodeDisplayCompleteness:
    """Property 3: Episode Display Completeness

    Feature: podtext, Property 3: Episode Display Completeness

    For any list of EpisodeInfo objects, the formatted display output
    SHALL contain the title, publication date, and index number for each episode.

    **Validates: Requirements 2.2**
    """

    @settings(max_examples=100)
    @given(episodes=episode_info_list_strategy(min_size=0, max_size=20))
    def test_format_episode_results_contains_all_titles(
        self,
        episodes: list[EpisodeInfo],
    ) -> None:
        """Property 3: Episode Display Completeness - Titles

        Feature: podtext, Property 3: Episode Display Completeness

        For any list of EpisodeInfo objects, the formatted display output
        SHALL contain the title for each episode.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results(episodes)

        for episode in episodes:
            # Property: Output SHALL contain the title for each episode
            assert episode.title in output, (
                f"Output should contain title '{episode.title}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(episodes=episode_info_list_strategy(min_size=0, max_size=20))
    def test_format_episode_results_contains_all_pub_dates(
        self,
        episodes: list[EpisodeInfo],
    ) -> None:
        """Property 3: Episode Display Completeness - Publication Dates

        Feature: podtext, Property 3: Episode Display Completeness

        For any list of EpisodeInfo objects, the formatted display output
        SHALL contain the publication date for each episode.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results(episodes)

        for episode in episodes:
            # Format date as YYYY-MM-DD (matching the implementation)
            date_str = episode.pub_date.strftime("%Y-%m-%d")

            # Property: Output SHALL contain the publication date for each episode
            assert date_str in output, (
                f"Output should contain publication date '{date_str}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(episodes=episode_info_list_strategy(min_size=0, max_size=20))
    def test_format_episode_results_contains_all_indices(
        self,
        episodes: list[EpisodeInfo],
    ) -> None:
        """Property 3: Episode Display Completeness - Index Numbers

        Feature: podtext, Property 3: Episode Display Completeness

        For any list of EpisodeInfo objects, the formatted display output
        SHALL contain the index number for each episode.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results(episodes)

        for episode in episodes:
            # The index is displayed as "N. " at the start of a line
            index_pattern = f"{episode.index}."

            # Property: Output SHALL contain the index number for each episode
            assert index_pattern in output, (
                f"Output should contain index '{index_pattern}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(episodes=episode_info_list_strategy(min_size=0, max_size=20))
    def test_format_episode_results_contains_title_date_and_index(
        self,
        episodes: list[EpisodeInfo],
    ) -> None:
        """Property 3: Episode Display Completeness - Combined

        Feature: podtext, Property 3: Episode Display Completeness

        For any list of EpisodeInfo objects, the formatted display output
        SHALL contain the title, publication date, and index number for each episode.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results(episodes)

        for episode in episodes:
            # Format date as YYYY-MM-DD (matching the implementation)
            date_str = episode.pub_date.strftime("%Y-%m-%d")
            index_pattern = f"{episode.index}."

            # Property: Output SHALL contain title, publication date, and index for each episode
            assert episode.title in output, (
                f"Output should contain title '{episode.title}', but it was not found.\n"
                f"Output:\n{output}"
            )
            assert date_str in output, (
                f"Output should contain publication date '{date_str}', but it was not found.\n"
                f"Output:\n{output}"
            )
            assert index_pattern in output, (
                f"Output should contain index '{index_pattern}', but it was not found.\n"
                f"Output:\n{output}"
            )

    @settings(max_examples=100)
    @given(episodes=episode_info_list_strategy(min_size=1, max_size=20))
    def test_format_episode_results_non_empty_list_produces_output(
        self,
        episodes: list[EpisodeInfo],
    ) -> None:
        """Property 3: Episode Display Completeness - Non-empty output

        Feature: podtext, Property 3: Episode Display Completeness

        For any non-empty list of EpisodeInfo objects, the formatted
        display output SHALL be non-empty and contain meaningful content.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results(episodes)

        # Property: Non-empty input SHALL produce non-empty output
        assert output, "Non-empty episodes list should produce non-empty output"
        assert output != "No episodes found.", (
            "Non-empty episodes list should not produce 'No episodes found.' message"
        )

    @settings(max_examples=100)
    @given(episode=episode_info_strategy())
    def test_format_episode_results_single_episode(
        self,
        episode: EpisodeInfo,
    ) -> None:
        """Property 3: Episode Display Completeness - Single episode

        Feature: podtext, Property 3: Episode Display Completeness

        For a single EpisodeInfo object, the formatted display output
        SHALL contain the title, publication date, and index number.

        **Validates: Requirements 2.2**
        """
        output = format_episode_results([episode])

        # Format date as YYYY-MM-DD (matching the implementation)
        date_str = episode.pub_date.strftime("%Y-%m-%d")
        index_pattern = f"{episode.index}."

        # Property: Output SHALL contain title, publication date, and index
        assert episode.title in output, (
            f"Output should contain title '{episode.title}', but it was not found.\n"
            f"Output:\n{output}"
        )
        assert date_str in output, (
            f"Output should contain publication date '{date_str}', but it was not found.\n"
            f"Output:\n{output}"
        )
        assert index_pattern in output, (
            f"Output should contain index '{index_pattern}', but it was not found.\n"
            f"Output:\n{output}"
        )


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEmptyListHandling:
    """Tests for empty list handling in display functions.

    Feature: podtext

    Validates proper handling of empty input lists.
    """

    def test_format_search_results_empty_list(self) -> None:
        """Test that empty search results list produces appropriate message.

        Feature: podtext, Property 2: Search Result Display Completeness

        **Validates: Requirements 1.2**
        """
        output = format_search_results([])
        assert output == "No podcasts found.", (
            f"Empty results should produce 'No podcasts found.', got: '{output}'"
        )

    def test_format_episode_results_empty_list(self) -> None:
        """Test that empty episode list produces appropriate message.

        Feature: podtext, Property 3: Episode Display Completeness

        **Validates: Requirements 2.2**
        """
        output = format_episode_results([])
        assert output == "No episodes found.", (
            f"Empty episodes should produce 'No episodes found.', got: '{output}'"
        )
