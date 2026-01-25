"""Unit tests for batch transcription functionality.

Feature: batch-transcribe
Tests the BatchResult dataclass and batch processing utilities.

Validates: Requirements 3.3, 5.4
"""

from __future__ import annotations

from typing import Any

from click.testing import CliRunner
from hypothesis import given, settings
from hypothesis import strategies as st

from podtext.cli.main import BatchResult, cli, deduplicate_indices


class TestBatchResult:
    """Tests for BatchResult dataclass.

    Feature: batch-transcribe

    Validates: Requirements 3.3, 5.4
    """

    def test_batch_result_success(self) -> None:
        """Test BatchResult creation for successful episode processing.

        Feature: batch-transcribe

        **Validates: Requirements 3.3, 5.4**
        """
        result = BatchResult(
            index=1,
            success=True,
            output_path="/path/to/output.md",
            error_message=None,
        )

        assert result.index == 1
        assert result.success is True
        assert result.output_path == "/path/to/output.md"
        assert result.error_message is None

    def test_batch_result_failure(self) -> None:
        """Test BatchResult creation for failed episode processing.

        Feature: batch-transcribe

        **Validates: Requirements 3.3, 5.4**
        """
        result = BatchResult(
            index=2,
            success=False,
            output_path=None,
            error_message="Index out of range",
        )

        assert result.index == 2
        assert result.success is False
        assert result.output_path is None
        assert result.error_message == "Index out of range"

    def test_batch_result_type_hints(self) -> None:
        """Test that BatchResult accepts correct types.

        Feature: batch-transcribe

        **Validates: Requirements 3.3, 5.4**
        """
        # Test with all fields
        result1 = BatchResult(
            index=5,
            success=True,
            output_path="/some/path.md",
            error_message=None,
        )
        assert isinstance(result1.index, int)
        assert isinstance(result1.success, bool)
        assert isinstance(result1.output_path, str)
        assert result1.error_message is None

        # Test with None values
        result2 = BatchResult(
            index=10,
            success=False,
            output_path=None,
            error_message="Some error",
        )
        assert isinstance(result2.index, int)
        assert isinstance(result2.success, bool)
        assert result2.output_path is None
        assert isinstance(result2.error_message, str)


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing with multiple indices.

    Feature: batch-transcribe

    Tests that the transcribe command correctly accepts single and multiple
    episode indices, and properly rejects empty input.

    Validates: Requirements 1.1, 1.4, 1.5
    """

    def test_single_index_backward_compatibility(self) -> None:
        """Test that single index argument works (backward compatibility).

        Feature: batch-transcribe

        The CLI should accept a single index argument to maintain backward
        compatibility with the original single-episode transcription workflow.

        **Validates: Requirements 1.1, 1.5**
        """
        runner = CliRunner()
        # Use a fake feed URL - we're only testing argument parsing
        # The command will fail later due to missing config/invalid URL,
        # but that's after argument parsing succeeds
        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "1"])
        
        # If argument parsing failed, Click would show "Error: Missing argument"
        # or similar. We expect it to fail later (config/network), not on parsing.
        # Check that we don't get Click's argument parsing errors
        assert "Missing argument" not in result.output
        assert "Invalid value" not in result.output or "INDEX" not in result.output

    def test_multiple_indices_accepted(self) -> None:
        """Test that multiple index arguments are accepted.

        Feature: batch-transcribe

        The CLI should accept multiple index arguments for batch processing
        of multiple episodes in a single command invocation.

        **Validates: Requirements 1.1, 1.4**
        """
        runner = CliRunner()
        # Test with multiple indices
        result = runner.invoke(
            cli, 
            ["transcribe", "https://example.com/feed.xml", "1", "2", "3"]
        )
        
        # Check that argument parsing succeeded (no Click parsing errors)
        assert "Missing argument" not in result.output
        assert "Invalid value" not in result.output or "INDEX" not in result.output

    def test_empty_indices_error(self) -> None:
        """Test that empty index input produces an error.

        Feature: batch-transcribe

        The CLI should require at least one index argument and display an
        error message when no indices are provided.

        **Validates: Requirements 1.4**
        """
        runner = CliRunner()
        # Test with no indices - should fail at argument parsing
        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml"])
        
        # Click should report missing required argument
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()

    def test_multiple_indices_with_duplicates(self) -> None:
        """Test that multiple indices including duplicates are accepted.

        Feature: batch-transcribe

        The CLI should accept multiple indices even if they contain duplicates.
        Deduplication happens after argument parsing.

        **Validates: Requirements 1.1, 1.4**
        """
        runner = CliRunner()
        # Test with duplicate indices
        result = runner.invoke(
            cli,
            ["transcribe", "https://example.com/feed.xml", "1", "3", "1", "2"]
        )
        
        # Check that argument parsing succeeded
        assert "Missing argument" not in result.output
        assert "Invalid value" not in result.output or "INDEX" not in result.output

    def test_non_integer_index_rejected(self) -> None:
        """Test that non-integer index values are rejected.

        Feature: batch-transcribe

        The CLI should validate that index arguments are integers and reject
        non-integer values with an appropriate error message.

        **Validates: Requirements 1.1**
        """
        runner = CliRunner()
        # Test with non-integer index
        result = runner.invoke(
            cli,
            ["transcribe", "https://example.com/feed.xml", "abc"]
        )
        
        # Click should report invalid value for integer type
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "integer" in result.output.lower()


class TestDeduplicateIndices:
    """Tests for deduplicate_indices function.

    Feature: batch-transcribe

    Validates: Requirements 1.3
    """

    def test_no_duplicates(self) -> None:
        """Test deduplication with no duplicate indices.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (1, 2, 3, 4, 5)
        result = deduplicate_indices(indices)
        assert result == [1, 2, 3, 4, 5]

    def test_with_duplicates(self) -> None:
        """Test deduplication with duplicate indices.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (1, 3, 2, 3, 1, 5)
        result = deduplicate_indices(indices)
        assert result == [1, 3, 2, 5]

    def test_all_duplicates(self) -> None:
        """Test deduplication when all indices are the same.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (7, 7, 7, 7)
        result = deduplicate_indices(indices)
        assert result == [7]

    def test_empty_tuple(self) -> None:
        """Test deduplication with empty input.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = ()
        result = deduplicate_indices(indices)
        assert result == []

    def test_single_index(self) -> None:
        """Test deduplication with single index.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (42,)
        result = deduplicate_indices(indices)
        assert result == [42]

    def test_preserves_first_occurrence_order(self) -> None:
        """Test that first occurrence order is preserved.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (5, 1, 3, 1, 2, 5, 3, 4)
        result = deduplicate_indices(indices)
        # Should keep: 5 (first), 1 (first), 3 (first), 2 (first), 4 (first)
        assert result == [5, 1, 3, 2, 4]

    def test_consecutive_duplicates(self) -> None:
        """Test deduplication with consecutive duplicate indices.

        Feature: batch-transcribe

        **Validates: Requirements 1.3**
        """
        indices = (1, 1, 2, 2, 3, 3)
        result = deduplicate_indices(indices)
        assert result == [1, 2, 3]


# =============================================================================
# Property-Based Tests
# =============================================================================


class TestDeduplicationPreservesOrder:
    """Property 3: Deduplication Preserves Order

    Feature: batch-transcribe, Property 3: Deduplication Preserves Order

    For any list of indices containing duplicates, the processing order should
    contain each unique index exactly once, appearing in the position of its
    first occurrence in the input list.

    **Validates: Requirements 1.3**
    """

    @settings(max_examples=100)
    @given(indices=st.lists(st.integers(min_value=1, max_value=100), min_size=0, max_size=50))
    def test_deduplication_preserves_first_occurrence_order(
        self,
        indices: list[int],
    ) -> None:
        """Property 3: Deduplication Preserves Order

        Feature: batch-transcribe, Property 3: Deduplication Preserves Order

        For any list of indices, the deduplicated result should contain each
        unique index exactly once, in the order of its first occurrence.

        **Validates: Requirements 1.3**
        """
        # Convert list to tuple as the function expects
        indices_tuple = tuple(indices)
        result = deduplicate_indices(indices_tuple)

        # Property 1: Each unique index appears exactly once
        assert len(result) == len(set(result)), (
            f"Result should contain no duplicates, but got: {result}"
        )

        # Property 2: All unique indices from input are in result
        unique_input = set(indices)
        unique_result = set(result)
        assert unique_input == unique_result, (
            f"Result should contain all unique indices from input.\n"
            f"Input unique: {unique_input}\n"
            f"Result unique: {unique_result}"
        )

        # Property 3: Order is preserved based on first occurrence
        # Build expected order by tracking first occurrences
        expected_order = []
        seen = set()
        for idx in indices:
            if idx not in seen:
                expected_order.append(idx)
                seen.add(idx)

        assert result == expected_order, (
            f"Result should preserve first occurrence order.\n"
            f"Input: {indices}\n"
            f"Expected: {expected_order}\n"
            f"Got: {result}"
        )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=20),
            min_size=1,
            max_size=50,
        )
    )
    def test_deduplication_result_is_subset_of_input(
        self,
        indices: list[int],
    ) -> None:
        """Property 3: Deduplication result is subset of input

        Feature: batch-transcribe, Property 3: Deduplication Preserves Order

        For any non-empty list of indices, every element in the deduplicated
        result must have appeared in the original input.

        **Validates: Requirements 1.3**
        """
        indices_tuple = tuple(indices)
        result = deduplicate_indices(indices_tuple)

        # Property: Every element in result must be in input
        for idx in result:
            assert idx in indices, (
                f"Result contains index {idx} which was not in input: {indices}"
            )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=20),
            min_size=1,
            max_size=50,
        )
    )
    def test_deduplication_length_bounded_by_input(
        self,
        indices: list[int],
    ) -> None:
        """Property 3: Deduplication length is bounded by input length

        Feature: batch-transcribe, Property 3: Deduplication Preserves Order

        For any list of indices, the deduplicated result should have length
        less than or equal to the input length.

        **Validates: Requirements 1.3**
        """
        indices_tuple = tuple(indices)
        result = deduplicate_indices(indices_tuple)

        # Property: Result length <= input length
        assert len(result) <= len(indices), (
            f"Result length ({len(result)}) should not exceed input length ({len(indices)})"
        )

    @settings(max_examples=100)
    @given(
        unique_indices=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=0,
            max_size=30,
            unique=True,
        )
    )
    def test_deduplication_with_no_duplicates_preserves_input(
        self,
        unique_indices: list[int],
    ) -> None:
        """Property 3: Deduplication with no duplicates preserves input

        Feature: batch-transcribe, Property 3: Deduplication Preserves Order

        For any list of unique indices (no duplicates), the deduplicated result
        should be identical to the input.

        **Validates: Requirements 1.3**
        """
        indices_tuple = tuple(unique_indices)
        result = deduplicate_indices(indices_tuple)

        # Property: When input has no duplicates, result equals input
        assert result == unique_indices, (
            f"When input has no duplicates, result should equal input.\n"
            f"Input: {unique_indices}\n"
            f"Result: {result}"
        )

    @settings(max_examples=100)
    @given(
        index=st.integers(min_value=1, max_value=100),
        count=st.integers(min_value=1, max_value=20),
    )
    def test_deduplication_with_all_same_returns_single_element(
        self,
        index: int,
        count: int,
    ) -> None:
        """Property 3: Deduplication with all same values returns single element

        Feature: batch-transcribe, Property 3: Deduplication Preserves Order

        For any list where all indices are the same value, the deduplicated
        result should contain exactly one element with that value.

        **Validates: Requirements 1.3**
        """
        indices_tuple = tuple([index] * count)
        result = deduplicate_indices(indices_tuple)

        # Property: All same values should result in single-element list
        assert result == [index], (
            f"When all indices are {index}, result should be [{index}], got: {result}"
        )
        assert len(result) == 1, (
            f"Result should have exactly one element, got {len(result)}"
        )


# =============================================================================
# Unit Tests for process_batch function
# =============================================================================


class TestProcessBatch:
    """Tests for process_batch function.

    Feature: batch-transcribe

    Tests the batch processing orchestrator that handles multiple episodes
    sequentially.

    Validates: Requirements 2.1, 5.1
    """

    def test_process_batch_deduplicates_indices(self) -> None:
        """Test that process_batch deduplicates indices before processing.

        Feature: batch-transcribe

        The process_batch function should deduplicate indices to avoid
        processing the same episode multiple times.

        **Validates: Requirements 1.3, 2.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        # Mock the dependencies at their original module locations
        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episode_1 = MagicMock()
            mock_episode_1.index = 1
            mock_episode_2 = MagicMock()
            mock_episode_2.index = 2

            mock_parse_feed.return_value = [mock_episode_1, mock_episode_2]

            # Mock successful pipeline results
            mock_result_1 = MagicMock()
            mock_result_1.output_path = "/path/to/episode1.md"
            mock_result_2 = MagicMock()
            mock_result_2.output_path = "/path/to/episode2.md"

            mock_pipeline.side_effect = [mock_result_1, mock_result_2]

            # Call with duplicate indices
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1, 2, 1, 2),  # Duplicates
                skip_language_check=False,
            )

            # Should only process 2 unique episodes
            assert len(results) == 2
            assert mock_pipeline.call_count == 2

            # Verify both episodes were processed successfully
            assert results[0].index == 1
            assert results[0].success is True
            assert results[1].index == 2
            assert results[1].success is True

    def test_process_batch_displays_total_count(self, capsys: Any) -> None:
        """Test that process_batch displays the total episode count.

        Feature: batch-transcribe

        The process_batch function should display the total number of unique
        episodes to be processed at the start.

        **Validates: Requirements 5.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            mock_episode = MagicMock()
            mock_episode.index = 1
            mock_parse_feed.return_value = [mock_episode]

            mock_result = MagicMock()
            mock_result.output_path = "/path/to/episode.md"
            mock_pipeline.return_value = mock_result

            # Call with single episode
            process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1,),
                skip_language_check=False,
            )

            # Check output
            captured = capsys.readouterr()
            assert "Processing 1 episode from feed..." in captured.out

    def test_process_batch_handles_missing_episode(self) -> None:
        """Test that process_batch handles episodes not found in feed.

        Feature: batch-transcribe

        When an episode index is not found in the feed, process_batch should
        record a failure and continue processing remaining episodes.

        **Validates: Requirements 3.1, 3.4**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Only episode 1 exists in feed
            mock_episode = MagicMock()
            mock_episode.index = 1
            mock_parse_feed.return_value = [mock_episode]

            mock_result = MagicMock()
            mock_result.output_path = "/path/to/episode1.md"
            mock_pipeline.return_value = mock_result

            # Request episodes 1 and 99 (99 doesn't exist)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1, 99),
                skip_language_check=False,
            )

            # Should have 2 results: 1 success, 1 failure
            assert len(results) == 2

            # Episode 1 should succeed
            assert results[0].index == 1
            assert results[0].success is True

            # Episode 99 should fail
            assert results[1].index == 99
            assert results[1].success is False
            assert results[1].error_message is not None and "not found" in results[1].error_message.lower()

    def test_process_batch_continues_after_pipeline_failure(self) -> None:
        """Test that process_batch continues after a pipeline failure.

        Feature: batch-transcribe

        When one episode fails during pipeline processing, process_batch
        should continue processing remaining episodes.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create two episodes
            mock_episode_1 = MagicMock()
            mock_episode_1.index = 1
            mock_episode_2 = MagicMock()
            mock_episode_2.index = 2

            mock_parse_feed.return_value = [mock_episode_1, mock_episode_2]

            # First episode fails, second succeeds
            mock_result_2 = MagicMock()
            mock_result_2.output_path = "/path/to/episode2.md"

            mock_pipeline.side_effect = [None, mock_result_2]  # None = failure

            # Process both episodes
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1, 2),
                skip_language_check=False,
            )

            # Should have 2 results
            assert len(results) == 2

            # Episode 1 should fail
            assert results[0].index == 1
            assert results[0].success is False

            # Episode 2 should succeed
            assert results[1].index == 2
            assert results[1].success is True


# =============================================================================
# Property-Based Tests for Sequential Processing
# =============================================================================


class TestSequentialProcessingOrder:
    """Property 4: Sequential Processing Order

    Feature: batch-transcribe, Property 4: Sequential Processing Order

    For any list of valid indices, the episodes should be processed in the
    exact order specified in the input, with each episode's processing
    completing before the next begins.

    **Validates: Requirements 2.1**
    """

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=20),
            min_size=1,
            max_size=10,
        )
    )
    def test_episodes_processed_in_specified_order(
        self,
        indices: list[int],
    ) -> None:
        """Property 4: Episodes are processed in the exact order specified.

        Feature: batch-transcribe, Property 4: Sequential Processing Order

        For any list of indices, the results should be returned in the same
        order as the deduplicated input indices, proving sequential processing.

        **Validates: Requirements 2.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes for all possible indices
            mock_episodes = []
            for i in range(1, 21):  # Cover indices 1-20
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Mock successful pipeline results
            def create_mock_result(episode: MagicMock) -> MagicMock:
                mock_result = MagicMock()
                mock_result.output_path = f"/path/to/episode{episode.index}.md"
                return mock_result

            mock_pipeline.side_effect = lambda episode, **kwargs: create_mock_result(episode)

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Property 1: Results are in the same order as deduplicated input
            expected_order = deduplicate_indices(indices_tuple)
            result_indices = [r.index for r in results]

            assert result_indices == expected_order, (
                f"Results should be in the same order as deduplicated input.\n"
                f"Input: {indices}\n"
                f"Expected order: {expected_order}\n"
                f"Result order: {result_indices}"
            )

            # Property 2: Number of results matches number of unique indices
            assert len(results) == len(expected_order), (
                f"Number of results ({len(results)}) should match "
                f"number of unique indices ({len(expected_order)})"
            )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=15),
            min_size=2,
            max_size=8,
        )
    )
    def test_pipeline_called_sequentially_not_parallel(
        self,
        indices: list[int],
    ) -> None:
        """Property 4: Pipeline is called sequentially, not in parallel.

        Feature: batch-transcribe, Property 4: Sequential Processing Order

        For any list of indices, the pipeline should be called once for each
        unique index, and each call should complete before the next begins.
        This is verified by checking that pipeline calls happen in order.

        **Validates: Requirements 2.1**
        """
        from unittest.mock import MagicMock, call, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, 16):  # Cover indices 1-15
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track call order
            call_order = []

            def track_pipeline_call(episode: MagicMock, **kwargs: object) -> MagicMock:
                call_order.append(episode.index)
                mock_result = MagicMock()
                mock_result.output_path = f"/path/to/episode{episode.index}.md"
                return mock_result

            mock_pipeline.side_effect = track_pipeline_call

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Property: Pipeline calls happen in the expected order
            expected_order = deduplicate_indices(indices_tuple)

            assert call_order == expected_order, (
                f"Pipeline should be called in sequential order.\n"
                f"Input: {indices}\n"
                f"Expected call order: {expected_order}\n"
                f"Actual call order: {call_order}"
            )

            # Property: Number of pipeline calls matches unique indices
            assert len(call_order) == len(expected_order), (
                f"Pipeline should be called once per unique index.\n"
                f"Expected calls: {len(expected_order)}\n"
                f"Actual calls: {len(call_order)}"
            )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=10),
            min_size=1,
            max_size=6,
        )
    )
    def test_each_episode_completes_before_next_begins(
        self,
        indices: list[int],
    ) -> None:
        """Property 4: Each episode completes before the next begins.

        Feature: batch-transcribe, Property 4: Sequential Processing Order

        For any list of indices, each episode's processing (including all
        pipeline stages) should complete before the next episode begins.
        This is verified by tracking when each episode starts and completes.

        **Validates: Requirements 2.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, 11):  # Cover indices 1-10
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track episode lifecycle: (index, event_type, timestamp)
            lifecycle_events: list[tuple[int, str, int]] = []
            timestamp = [0]  # Use list to allow mutation in nested function

            def track_pipeline_call(episode: MagicMock, **kwargs: object) -> MagicMock:
                # Record start
                lifecycle_events.append((episode.index, "start", timestamp[0]))
                timestamp[0] += 1

                # Simulate processing time
                mock_result = MagicMock()
                mock_result.output_path = f"/path/to/episode{episode.index}.md"

                # Record completion
                lifecycle_events.append((episode.index, "complete", timestamp[0]))
                timestamp[0] += 1

                return mock_result

            mock_pipeline.side_effect = track_pipeline_call

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Property: For each episode, its completion happens before the next episode starts
            expected_order = deduplicate_indices(indices_tuple)

            for i in range(len(expected_order) - 1):
                current_idx = expected_order[i]
                next_idx = expected_order[i + 1]

                # Find completion time of current episode
                current_complete_time = None
                for idx, event, time in lifecycle_events:
                    if idx == current_idx and event == "complete":
                        current_complete_time = time
                        break

                # Find start time of next episode
                next_start_time = None
                for idx, event, time in lifecycle_events:
                    if idx == next_idx and event == "start":
                        next_start_time = time
                        break

                assert current_complete_time is not None, (
                    f"Episode {current_idx} should have completed"
                )
                assert next_start_time is not None, (
                    f"Episode {next_idx} should have started"
                )
                assert current_complete_time < next_start_time, (
                    f"Episode {current_idx} should complete (time {current_complete_time}) "
                    f"before episode {next_idx} starts (time {next_start_time})"
                )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=12),
            min_size=1,
            max_size=7,
            unique=True,  # No duplicates for this test
        )
    )
    def test_no_parallel_processing_with_unique_indices(
        self,
        indices: list[int],
    ) -> None:
        """Property 4: No parallel processing occurs with unique indices.

        Feature: batch-transcribe, Property 4: Sequential Processing Order

        For any list of unique indices, episodes should be processed one at a
        time with no overlap. This is verified by ensuring no two episodes are
        being processed simultaneously.

        **Validates: Requirements 2.1, 2.4**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, 13):  # Cover indices 1-12
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track active episodes (episodes currently being processed)
            active_episodes: list[int] = []
            max_concurrent = [0]  # Use list to allow mutation

            def track_pipeline_call(episode: MagicMock, **kwargs: object) -> MagicMock:
                # Start processing
                active_episodes.append(episode.index)
                max_concurrent[0] = max(max_concurrent[0], len(active_episodes))

                # Create result
                mock_result = MagicMock()
                mock_result.output_path = f"/path/to/episode{episode.index}.md"

                # Complete processing
                active_episodes.remove(episode.index)

                return mock_result

            mock_pipeline.side_effect = track_pipeline_call

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Property: Maximum concurrent episodes should be 1 (sequential processing)
            assert max_concurrent[0] == 1, (
                f"Episodes should be processed sequentially (max concurrent = 1), "
                f"but found max concurrent = {max_concurrent[0]}"
            )

            # Property: All episodes completed successfully
            assert len(results) == len(indices), (
                f"All {len(indices)} episodes should be processed"
            )


    def test_process_batch_handles_config_error(self) -> None:
        """Test that process_batch handles configuration errors gracefully.

        Feature: batch-transcribe

        When configuration cannot be loaded, process_batch should return
        failure results for all episodes.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import patch

        from podtext.cli.main import process_batch
        from podtext.core.config import ConfigError

        with patch("podtext.core.config.load_config") as mock_load_config:
            # Simulate config error
            mock_load_config.side_effect = ConfigError("Config file not found")

            # Process episodes
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1, 2),
                skip_language_check=False,
            )

            # Should have failure results for all episodes
            assert len(results) == 2
            assert all(not r.success for r in results)
            assert all(r.error_message is not None and "Configuration error" in r.error_message for r in results)

    def test_process_batch_handles_feed_error(self) -> None:
        """Test that process_batch handles RSS feed errors gracefully.

        Feature: batch-transcribe

        When the RSS feed cannot be parsed, process_batch should return
        failure results for all episodes.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch
        from podtext.services.rss import RSSFeedError

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Simulate feed error
            mock_parse_feed.side_effect = RSSFeedError("Invalid feed")

            # Process episodes
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=(1, 2),
                skip_language_check=False,
            )

            # Should have failure results for all episodes
            assert len(results) == 2
            assert all(not r.success for r in results)
            assert all(r.error_message is not None and "Feed error" in r.error_message for r in results)


# =============================================================================
# Property-Based Tests for Error Isolation
# =============================================================================


class TestErrorIsolation:
    """Property 6: Error Isolation

    Feature: batch-transcribe, Property 6: Error Isolation

    For any batch where one or more episodes fail, the failure of any episode
    should not prevent the processing of subsequent episodes in the batch.

    **Validates: Requirements 3.1**
    """

    @settings(max_examples=100)
    @given(
        total_episodes=st.integers(min_value=3, max_value=10),
        failure_positions=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    def test_failures_do_not_stop_subsequent_processing(
        self,
        total_episodes: int,
        failure_positions: list[int],
    ) -> None:
        """Property 6: Failures do not stop subsequent episode processing.

        Feature: batch-transcribe, Property 6: Error Isolation

        For any batch of episodes where some episodes fail, all episodes
        should be attempted regardless of failures. The number of results
        should equal the number of unique indices requested.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import process_batch

        # Filter failure positions to be within range
        valid_failures = [pos for pos in failure_positions if pos < total_episodes]
        if not valid_failures:
            # If no valid failures, make the first episode fail
            valid_failures = [0]

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, total_episodes + 1):
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track which episodes were attempted
            attempted_episodes = []

            def pipeline_with_failures(episode: MagicMock, **kwargs: object) -> MagicMock | None:
                attempted_episodes.append(episode.index)
                # Fail at specified positions (0-indexed)
                position = episode.index - 1
                if position in valid_failures:
                    return None  # Failure
                else:
                    mock_result = MagicMock()
                    mock_result.output_path = f"/path/to/episode{episode.index}.md"
                    return mock_result

            mock_pipeline.side_effect = pipeline_with_failures

            # Create indices for all episodes
            indices = tuple(range(1, total_episodes + 1))

            # Process the batch
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices,
                skip_language_check=False,
            )

            # Property 1: All episodes should be attempted
            assert len(attempted_episodes) == total_episodes, (
                f"All {total_episodes} episodes should be attempted, "
                f"but only {len(attempted_episodes)} were attempted"
            )

            # Property 2: Number of results equals number of episodes
            assert len(results) == total_episodes, (
                f"Should have {total_episodes} results, got {len(results)}"
            )

            # Property 3: Episodes after failures should still be processed
            for i in range(total_episodes):
                assert (i + 1) in attempted_episodes, (
                    f"Episode {i + 1} should have been attempted even if "
                    f"previous episodes failed"
                )

            # Property 4: Correct episodes failed
            for i, result in enumerate(results):
                if i in valid_failures:
                    assert not result.success, (
                        f"Episode at position {i} (index {result.index}) "
                        f"should have failed"
                    )
                else:
                    assert result.success, (
                        f"Episode at position {i} (index {result.index}) "
                        f"should have succeeded"
                    )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=15),
            min_size=2,
            max_size=8,
        ),
        failure_index=st.integers(min_value=1, max_value=15),
    )
    def test_single_failure_does_not_affect_others(
        self,
        indices: list[int],
        failure_index: int,
    ) -> None:
        """Property 6: A single failure does not affect other episodes.

        Feature: batch-transcribe, Property 6: Error Isolation

        For any batch where one specific episode fails, all other episodes
        should still be processed successfully.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes for all possible indices
            mock_episodes = []
            for i in range(1, 16):
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Pipeline fails for the specific failure_index, succeeds for others
            def pipeline_with_single_failure(episode: MagicMock, **kwargs: object) -> MagicMock | None:
                if episode.index == failure_index:
                    return None  # Failure
                else:
                    mock_result = MagicMock()
                    mock_result.output_path = f"/path/to/episode{episode.index}.md"
                    return mock_result

            mock_pipeline.side_effect = pipeline_with_single_failure

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Get expected unique indices
            unique_indices = deduplicate_indices(indices_tuple)

            # Property 1: All unique episodes should have results
            assert len(results) == len(unique_indices), (
                f"Should have {len(unique_indices)} results, got {len(results)}"
            )

            # Property 2: Only the failure_index should fail (if it's in the batch)
            for result in results:
                if result.index == failure_index:
                    assert not result.success, (
                        f"Episode {failure_index} should have failed"
                    )
                else:
                    assert result.success, (
                        f"Episode {result.index} should have succeeded, "
                        f"but failed even though only episode {failure_index} "
                        f"was supposed to fail"
                    )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=12),
            min_size=3,
            max_size=10,
        ),
    )
    def test_all_failures_still_processes_all_episodes(
        self,
        indices: list[int],
    ) -> None:
        """Property 6: All failures still processes all episodes.

        Feature: batch-transcribe, Property 6: Error Isolation

        Even when all episodes fail, each episode should still be attempted
        and have a corresponding failure result.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, 13):
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track attempted episodes
            attempted_episodes = []

            # All episodes fail
            def pipeline_all_fail(episode: MagicMock, **kwargs: object) -> None:
                attempted_episodes.append(episode.index)
                return None  # Always fail

            mock_pipeline.side_effect = pipeline_all_fail

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Get expected unique indices
            unique_indices = deduplicate_indices(indices_tuple)

            # Property 1: All unique episodes should be attempted
            assert len(attempted_episodes) == len(unique_indices), (
                f"All {len(unique_indices)} episodes should be attempted, "
                f"got {len(attempted_episodes)}"
            )

            # Property 2: All results should be failures
            assert len(results) == len(unique_indices), (
                f"Should have {len(unique_indices)} results, got {len(results)}"
            )
            assert all(not r.success for r in results), (
                "All results should be failures"
            )

            # Property 3: Each unique index should have been attempted
            for idx in unique_indices:
                assert idx in attempted_episodes, (
                    f"Episode {idx} should have been attempted"
                )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=10),
            min_size=2,
            max_size=7,
        ),
        first_n_fail=st.integers(min_value=1, max_value=5),
    )
    def test_early_failures_do_not_prevent_later_successes(
        self,
        indices: list[int],
        first_n_fail: int,
    ) -> None:
        """Property 6: Early failures do not prevent later successes.

        Feature: batch-transcribe, Property 6: Error Isolation

        When the first N episodes fail, the remaining episodes should still
        be processed and can succeed.

        **Validates: Requirements 3.1**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Create mock episodes
            mock_episodes = []
            for i in range(1, 11):
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Get unique indices to determine how many will actually be processed
            unique_indices = deduplicate_indices(tuple(indices))
            
            # Track processing order
            processing_order = []

            # First N episodes fail, rest succeed
            def pipeline_with_early_failures(episode: MagicMock, **kwargs: object) -> MagicMock | None:
                processing_order.append(episode.index)
                # Fail the first first_n_fail episodes in the unique list
                position = unique_indices.index(episode.index)
                if position < first_n_fail:
                    return None  # Failure
                else:
                    mock_result = MagicMock()
                    mock_result.output_path = f"/path/to/episode{episode.index}.md"
                    return mock_result

            mock_pipeline.side_effect = pipeline_with_early_failures

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Property 1: All episodes should be processed
            assert len(results) == len(unique_indices), (
                f"Should have {len(unique_indices)} results, got {len(results)}"
            )

            # Property 2: Episodes after the first N should succeed
            for i, result in enumerate(results):
                if i < first_n_fail:
                    assert not result.success, (
                        f"Episode at position {i} should have failed"
                    )
                else:
                    assert result.success, (
                        f"Episode at position {i} should have succeeded "
                        f"even though earlier episodes failed"
                    )

            # Property 3: All episodes were attempted in order
            assert processing_order == unique_indices, (
                f"Episodes should be processed in order.\n"
                f"Expected: {unique_indices}\n"
                f"Got: {processing_order}"
            )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=10),
            min_size=2,
            max_size=6,
        ),
    )
    def test_missing_episodes_do_not_stop_processing(
        self,
        indices: list[int],
    ) -> None:
        """Property 6: Missing episodes do not stop processing.

        Feature: batch-transcribe, Property 6: Error Isolation

        When some requested episodes are not found in the feed, the episodes
        that do exist should still be processed successfully.

        **Validates: Requirements 3.1, 3.4**
        """
        from unittest.mock import MagicMock, patch

        from podtext.cli.main import deduplicate_indices, process_batch

        with patch("podtext.core.config.load_config") as mock_load_config, \
             patch("podtext.services.rss.parse_feed") as mock_parse_feed, \
             patch("podtext.core.pipeline.run_pipeline_safe") as mock_pipeline:

            # Setup mocks
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            # Only create episodes for indices 1-5 (some requested may not exist)
            mock_episodes = []
            for i in range(1, 6):
                mock_episode = MagicMock()
                mock_episode.index = i
                mock_episodes.append(mock_episode)

            mock_parse_feed.return_value = mock_episodes

            # Track which episodes were sent to pipeline
            pipeline_calls = []

            def track_pipeline_calls(episode: MagicMock, **kwargs: object) -> MagicMock:
                pipeline_calls.append(episode.index)
                mock_result = MagicMock()
                mock_result.output_path = f"/path/to/episode{episode.index}.md"
                return mock_result

            mock_pipeline.side_effect = track_pipeline_calls

            # Process the batch
            indices_tuple = tuple(indices)
            results = process_batch(
                feed_url="https://example.com/feed.xml",
                indices=indices_tuple,
                skip_language_check=False,
            )

            # Get expected unique indices
            unique_indices = deduplicate_indices(indices_tuple)

            # Property 1: Should have results for all requested indices
            assert len(results) == len(unique_indices), (
                f"Should have {len(unique_indices)} results, got {len(results)}"
            )

            # Property 2: Episodes that exist should succeed
            for result in results:
                if result.index <= 5:  # Episodes 1-5 exist
                    assert result.success, (
                        f"Episode {result.index} exists and should succeed"
                    )
                else:  # Episodes > 5 don't exist
                    assert not result.success, (
                        f"Episode {result.index} doesn't exist and should fail"
                    )
                    assert result.error_message is not None and "not found" in result.error_message.lower(), (
                        f"Missing episode should have 'not found' error message"
                    )

            # Property 3: All existing episodes should be processed
            existing_indices = [idx for idx in unique_indices if idx <= 5]
            assert sorted(pipeline_calls) == sorted(existing_indices), (
                f"All existing episodes should be processed.\n"
                f"Expected: {sorted(existing_indices)}\n"
                f"Got: {sorted(pipeline_calls)}"
            )


# =============================================================================
# Unit Tests for display_summary function
# =============================================================================


class TestDisplaySummary:
    """Tests for display_summary function.

    Feature: batch-transcribe

    Tests the summary display function that shows counts of successful
    and failed episodes after batch processing.

    Validates: Requirements 3.3, 5.4
    """

    def test_display_summary_all_success(self, capsys: Any) -> None:
        """Test display_summary with all successful episodes.

        Feature: batch-transcribe

        When all episodes succeed, the summary should show only successful
        count with no failure count.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results = [
            BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
            BatchResult(index=2, success=True, output_path="/path/2.md", error_message=None),
            BatchResult(index=3, success=True, output_path="/path/3.md", error_message=None),
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "Batch processing complete:" in captured.out
        assert "✓ 3 successful" in captured.out
        assert "✗" not in captured.out  # No failures

    def test_display_summary_all_failure(self, capsys: Any) -> None:
        """Test display_summary with all failed episodes.

        Feature: batch-transcribe

        When all episodes fail, the summary should show only failure
        count with no success count.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results = [
            BatchResult(index=1, success=False, output_path=None, error_message="Error 1"),
            BatchResult(index=2, success=False, output_path=None, error_message="Error 2"),
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "Batch processing complete:" in captured.out
        assert "✗ 2 failed" in captured.out
        assert "✓" not in captured.out  # No successes

    def test_display_summary_mixed_results(self, capsys: Any) -> None:
        """Test display_summary with mixed success and failure.

        Feature: batch-transcribe

        When some episodes succeed and some fail, the summary should show
        both success and failure counts.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results = [
            BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
            BatchResult(index=2, success=False, output_path=None, error_message="Error"),
            BatchResult(index=3, success=True, output_path="/path/3.md", error_message=None),
            BatchResult(index=4, success=False, output_path=None, error_message="Error"),
            BatchResult(index=5, success=True, output_path="/path/5.md", error_message=None),
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "Batch processing complete:" in captured.out
        assert "✓ 3 successful" in captured.out
        assert "✗ 2 failed" in captured.out

    def test_display_summary_empty_results(self, capsys: Any) -> None:
        """Test display_summary with empty results list.

        Feature: batch-transcribe

        When no episodes were processed, the summary should indicate this.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results: list[BatchResult] = []

        display_summary(results)

        captured = capsys.readouterr()
        assert "No episodes were processed." in captured.out

    def test_display_summary_single_success(self, capsys: Any) -> None:
        """Test display_summary with single successful episode.

        Feature: batch-transcribe

        When a single episode succeeds, the summary should show count of 1.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results = [
            BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "Batch processing complete:" in captured.out
        assert "✓ 1 successful" in captured.out
        assert "✗" not in captured.out

    def test_display_summary_single_failure(self, capsys: Any) -> None:
        """Test display_summary with single failed episode.

        Feature: batch-transcribe

        When a single episode fails, the summary should show count of 1.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        results = [
            BatchResult(index=1, success=False, output_path=None, error_message="Error"),
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "Batch processing complete:" in captured.out
        assert "✗ 1 failed" in captured.out
        assert "✓" not in captured.out

    def test_display_summary_counts_accuracy(self, capsys: Any) -> None:
        """Test that display_summary counts are accurate.

        Feature: batch-transcribe

        The counts displayed should exactly match the number of successes
        and failures in the results.

        **Validates: Requirements 3.3, 5.4**
        """
        from podtext.cli.main import display_summary

        # Create a larger batch with known counts
        results = [
            BatchResult(index=i, success=True, output_path=f"/path/{i}.md", error_message=None)
            for i in range(1, 8)  # 7 successes
        ] + [
            BatchResult(index=i, success=False, output_path=None, error_message="Error")
            for i in range(8, 11)  # 3 failures
        ]

        display_summary(results)

        captured = capsys.readouterr()
        assert "✓ 7 successful" in captured.out
        assert "✗ 3 failed" in captured.out


# =============================================================================
# Property-Based Tests for Summary Accuracy
# =============================================================================


class TestSummaryAccuracy:
    """Property 8: Summary Accuracy

    Feature: batch-transcribe, Property 8: Summary Accuracy

    For any completed batch, the summary display should show counts of
    successful and failed episodes that exactly match the actual number
    of successes and failures.

    **Validates: Requirements 3.3, 5.4**
    """

    @settings(max_examples=100)
    @given(
        success_count=st.integers(min_value=0, max_value=20),
        failure_count=st.integers(min_value=0, max_value=20),
    )
    def test_summary_counts_match_actual_results(
        self,
        success_count: int,
        failure_count: int,
    ) -> None:
        """Property 8: Summary counts exactly match actual successes and failures.

        Feature: batch-transcribe, Property 8: Summary Accuracy

        For any batch with a given number of successes and failures, the
        summary display should show counts that exactly match those numbers.

        **Validates: Requirements 3.3, 5.4**
        """
        import io
        import sys
        from contextlib import redirect_stdout

        from podtext.cli.main import display_summary

        # Skip if both counts are zero (empty batch handled separately)
        if success_count == 0 and failure_count == 0:
            return

        # Create results with the specified counts
        results = []
        
        # Add successful results
        for i in range(success_count):
            results.append(
                BatchResult(
                    index=i + 1,
                    success=True,
                    output_path=f"/path/to/episode{i + 1}.md",
                    error_message=None,
                )
            )
        
        # Add failed results
        for i in range(failure_count):
            results.append(
                BatchResult(
                    index=success_count + i + 1,
                    success=False,
                    output_path=None,
                    error_message=f"Error {i + 1}",
                )
            )

        # Capture output using StringIO
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            display_summary(results)
        
        captured_output = output_buffer.getvalue()

        # Property 1: If there are successes, the count should be displayed correctly
        if success_count > 0:
            assert f"✓ {success_count} successful" in captured_output, (
                f"Summary should show {success_count} successful episodes, "
                f"but output was: {captured_output}"
            )

        # Property 2: If there are failures, the count should be displayed correctly
        if failure_count > 0:
            assert f"✗ {failure_count} failed" in captured_output, (
                f"Summary should show {failure_count} failed episodes, "
                f"but output was: {captured_output}"
            )

        # Property 3: If there are no successes, success count should not appear
        if success_count == 0:
            assert "✓" not in captured_output, (
                "Summary should not show success count when there are no successes"
            )

        # Property 4: If there are no failures, failure count should not appear
        if failure_count == 0:
            assert "✗" not in captured_output, (
                "Summary should not show failure count when there are no failures"
            )

        # Property 5: Total results should equal sum of successes and failures
        assert len(results) == success_count + failure_count, (
            f"Total results ({len(results)}) should equal "
            f"success_count ({success_count}) + failure_count ({failure_count})"
        )

    @settings(max_examples=100)
    @given(
        results_data=st.lists(
            st.booleans(),  # True = success, False = failure
            min_size=1,
            max_size=30,
        )
    )
    def test_summary_counts_match_arbitrary_result_patterns(
        self,
        results_data: list[bool],
    ) -> None:
        """Property 8: Summary counts match for arbitrary success/failure patterns.

        Feature: batch-transcribe, Property 8: Summary Accuracy

        For any arbitrary pattern of successes and failures, the summary
        should accurately count and display the correct numbers.

        **Validates: Requirements 3.3, 5.4**
        """
        import io
        from contextlib import redirect_stdout

        from podtext.cli.main import display_summary

        # Create results based on the boolean pattern
        results = []
        for i, is_success in enumerate(results_data):
            if is_success:
                results.append(
                    BatchResult(
                        index=i + 1,
                        success=True,
                        output_path=f"/path/to/episode{i + 1}.md",
                        error_message=None,
                    )
                )
            else:
                results.append(
                    BatchResult(
                        index=i + 1,
                        success=False,
                        output_path=None,
                        error_message=f"Error for episode {i + 1}",
                    )
                )

        # Calculate expected counts
        expected_success_count = sum(1 for r in results if r.success)
        expected_failure_count = sum(1 for r in results if not r.success)

        # Capture output using StringIO
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            display_summary(results)
        
        captured_output = output_buffer.getvalue()

        # Property: Displayed counts must match actual counts
        if expected_success_count > 0:
            assert f"✓ {expected_success_count} successful" in captured_output, (
                f"Summary should show {expected_success_count} successful episodes, "
                f"but output was: {captured_output}"
            )
        else:
            assert "✓" not in captured_output, (
                "Summary should not show success count when there are no successes"
            )

        if expected_failure_count > 0:
            assert f"✗ {expected_failure_count} failed" in captured_output, (
                f"Summary should show {expected_failure_count} failed episodes, "
                f"but output was: {captured_output}"
            )
        else:
            assert "✗" not in captured_output, (
                "Summary should not show failure count when there are no failures"
            )

        # Property: Total count is preserved
        assert len(results) == len(results_data), (
            f"Total results ({len(results)}) should match input size ({len(results_data)})"
        )

    @settings(max_examples=100)
    @given(
        total_episodes=st.integers(min_value=1, max_value=25),
        success_ratio=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_summary_counts_with_varying_success_ratios(
        self,
        total_episodes: int,
        success_ratio: float,
    ) -> None:
        """Property 8: Summary counts are accurate for varying success ratios.

        Feature: batch-transcribe, Property 8: Summary Accuracy

        For any batch size and success ratio, the summary should accurately
        reflect the actual distribution of successes and failures.

        **Validates: Requirements 3.3, 5.4**
        """
        import io
        from contextlib import redirect_stdout

        from podtext.cli.main import display_summary

        # Calculate how many episodes should succeed
        success_count = int(total_episodes * success_ratio)
        failure_count = total_episodes - success_count

        # Create results
        results = []
        
        # Add successes
        for i in range(success_count):
            results.append(
                BatchResult(
                    index=i + 1,
                    success=True,
                    output_path=f"/path/to/episode{i + 1}.md",
                    error_message=None,
                )
            )
        
        # Add failures
        for i in range(failure_count):
            results.append(
                BatchResult(
                    index=success_count + i + 1,
                    success=False,
                    output_path=None,
                    error_message=f"Error {i + 1}",
                )
            )

        # Capture output using StringIO
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            display_summary(results)
        
        captured_output = output_buffer.getvalue()

        # Property: Counts in output match actual counts
        actual_success_count = sum(1 for r in results if r.success)
        actual_failure_count = sum(1 for r in results if not r.success)

        assert actual_success_count == success_count, (
            f"Actual success count should match expected: {success_count}"
        )
        assert actual_failure_count == failure_count, (
            f"Actual failure count should match expected: {failure_count}"
        )

        if success_count > 0:
            assert f"✓ {success_count} successful" in captured_output, (
                f"Summary should show {success_count} successful episodes"
            )

        if failure_count > 0:
            assert f"✗ {failure_count} failed" in captured_output, (
                f"Summary should show {failure_count} failed episodes"
            )

    @settings(max_examples=100)
    @given(
        indices=st.lists(
            st.integers(min_value=1, max_value=20),
            min_size=1,
            max_size=15,
        ),
        failure_indices=st.sets(
            st.integers(min_value=1, max_value=20),
            max_size=10,
        ),
    )
    def test_summary_accuracy_with_simulated_batch_processing(
        self,
        indices: list[int],
        failure_indices: set[int],
    ) -> None:
        """Property 8: Summary accuracy with simulated batch processing.

        Feature: batch-transcribe, Property 8: Summary Accuracy

        For any batch of episodes where specific indices fail, the summary
        should accurately count successes and failures based on which
        episodes actually failed.

        **Validates: Requirements 3.3, 5.4**
        """
        import io
        from contextlib import redirect_stdout

        from podtext.cli.main import deduplicate_indices, display_summary

        # Deduplicate indices as the real batch processing would
        unique_indices = deduplicate_indices(tuple(indices))

        # Create results based on whether each index is in failure_indices
        results = []
        for idx in unique_indices:
            if idx in failure_indices:
                results.append(
                    BatchResult(
                        index=idx,
                        success=False,
                        output_path=None,
                        error_message=f"Episode {idx} failed",
                    )
                )
            else:
                results.append(
                    BatchResult(
                        index=idx,
                        success=True,
                        output_path=f"/path/to/episode{idx}.md",
                        error_message=None,
                    )
                )

        # Calculate expected counts
        expected_success_count = sum(1 for r in results if r.success)
        expected_failure_count = sum(1 for r in results if not r.success)

        # Capture output using StringIO
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            display_summary(results)
        
        captured_output = output_buffer.getvalue()

        # Property: Summary counts match actual results
        if expected_success_count > 0:
            assert f"✓ {expected_success_count} successful" in captured_output, (
                f"Summary should show {expected_success_count} successful episodes, "
                f"but output was: {captured_output}"
            )

        if expected_failure_count > 0:
            assert f"✗ {expected_failure_count} failed" in captured_output, (
                f"Summary should show {expected_failure_count} failed episodes, "
                f"but output was: {captured_output}"
            )

        # Property: Total results equal unique indices
        assert len(results) == len(unique_indices), (
            f"Total results ({len(results)}) should match "
            f"unique indices count ({len(unique_indices)})"
        )

        # Property: Success + failure counts equal total
        assert expected_success_count + expected_failure_count == len(results), (
            f"Success count ({expected_success_count}) + "
            f"failure count ({expected_failure_count}) should equal "
            f"total results ({len(results)})"
        )

    @settings(max_examples=100)
    @given(
        all_success=st.booleans(),
        count=st.integers(min_value=1, max_value=30),
    )
    def test_summary_accuracy_for_all_same_outcome(
        self,
        all_success: bool,
        count: int,
    ) -> None:
        """Property 8: Summary accuracy when all episodes have same outcome.

        Feature: batch-transcribe, Property 8: Summary Accuracy

        When all episodes either succeed or fail, the summary should show
        only the relevant count (all successes or all failures).

        **Validates: Requirements 3.3, 5.4**
        """
        import io
        from contextlib import redirect_stdout

        from podtext.cli.main import display_summary

        # Create results with all same outcome
        results = []
        for i in range(count):
            if all_success:
                results.append(
                    BatchResult(
                        index=i + 1,
                        success=True,
                        output_path=f"/path/to/episode{i + 1}.md",
                        error_message=None,
                    )
                )
            else:
                results.append(
                    BatchResult(
                        index=i + 1,
                        success=False,
                        output_path=None,
                        error_message=f"Error {i + 1}",
                    )
                )

        # Capture output using StringIO
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            display_summary(results)
        
        captured_output = output_buffer.getvalue()

        # Property: Only the relevant count should appear
        if all_success:
            assert f"✓ {count} successful" in captured_output, (
                f"Summary should show {count} successful episodes"
            )
            assert "✗" not in captured_output, (
                "Summary should not show failure count when all succeed"
            )
        else:
            assert f"✗ {count} failed" in captured_output, (
                f"Summary should show {count} failed episodes"
            )
            assert "✓" not in captured_output, (
                "Summary should not show success count when all fail"
            )

        # Property: Total count matches input
        assert len(results) == count, (
            f"Total results ({len(results)}) should match count ({count})"
        )


# =============================================================================
# Unit Tests for transcribe command exit codes
# =============================================================================


class TestTranscribeCommandExitCodes:
    """Tests for transcribe command exit codes.

    Feature: batch-transcribe

    Tests that the transcribe command sets appropriate exit codes based on
    the success or failure of episode processing.

    Validates: Requirements 3.5
    """

    def test_exit_code_0_when_all_episodes_succeed(self) -> None:
        """Test that exit code is 0 when all episodes succeed.

        Feature: batch-transcribe

        When all episodes in a batch are processed successfully, the
        transcribe command should exit with code 0.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock successful results for all episodes
            mock_results = [
                BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
                BatchResult(index=2, success=True, output_path="/path/2.md", error_message=None),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1", "2"]
            )

            # Should exit with code 0 (success)
            assert result.exit_code == 0, (
                f"Exit code should be 0 when all episodes succeed, got {result.exit_code}"
            )

            # Verify process_batch was called
            mock_process_batch.assert_called_once()

            # Verify display_summary was called with results
            mock_display_summary.assert_called_once_with(mock_results)

    def test_exit_code_1_when_some_episodes_fail(self) -> None:
        """Test that exit code is 1 when some episodes fail.

        Feature: batch-transcribe

        When some episodes fail during batch processing, the transcribe
        command should exit with code 1.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock mixed results (some success, some failure)
            mock_results = [
                BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
                BatchResult(index=2, success=False, output_path=None, error_message="Error"),
                BatchResult(index=3, success=True, output_path="/path/3.md", error_message=None),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1", "2", "3"]
            )

            # Should exit with code 1 (failure)
            assert result.exit_code == 1, (
                f"Exit code should be 1 when some episodes fail, got {result.exit_code}"
            )

            # Verify process_batch was called
            mock_process_batch.assert_called_once()

            # Verify display_summary was called with results
            mock_display_summary.assert_called_once_with(mock_results)

    def test_exit_code_1_when_all_episodes_fail(self) -> None:
        """Test that exit code is 1 when all episodes fail.

        Feature: batch-transcribe

        When all episodes fail during batch processing, the transcribe
        command should exit with code 1.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock all failures
            mock_results = [
                BatchResult(index=1, success=False, output_path=None, error_message="Error 1"),
                BatchResult(index=2, success=False, output_path=None, error_message="Error 2"),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1", "2"]
            )

            # Should exit with code 1 (failure)
            assert result.exit_code == 1, (
                f"Exit code should be 1 when all episodes fail, got {result.exit_code}"
            )

            # Verify process_batch was called
            mock_process_batch.assert_called_once()

            # Verify display_summary was called with results
            mock_display_summary.assert_called_once_with(mock_results)

    def test_exit_code_0_with_single_successful_episode(self) -> None:
        """Test that exit code is 0 with single successful episode.

        Feature: batch-transcribe

        When a single episode is processed successfully, the transcribe
        command should exit with code 0 (backward compatibility).

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock single successful result
            mock_results = [
                BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command with single index
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1"]
            )

            # Should exit with code 0 (success)
            assert result.exit_code == 0, (
                f"Exit code should be 0 for single successful episode, got {result.exit_code}"
            )

            # Verify process_batch was called
            mock_process_batch.assert_called_once()

            # Verify display_summary was called with results
            mock_display_summary.assert_called_once_with(mock_results)

    def test_exit_code_1_with_single_failed_episode(self) -> None:
        """Test that exit code is 1 with single failed episode.

        Feature: batch-transcribe

        When a single episode fails during processing, the transcribe
        command should exit with code 1.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock single failed result
            mock_results = [
                BatchResult(index=1, success=False, output_path=None, error_message="Error"),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command with single index
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1"]
            )

            # Should exit with code 1 (failure)
            assert result.exit_code == 1, (
                f"Exit code should be 1 for single failed episode, got {result.exit_code}"
            )

            # Verify process_batch was called
            mock_process_batch.assert_called_once()

            # Verify display_summary was called with results
            mock_display_summary.assert_called_once_with(mock_results)

    def test_transcribe_calls_process_batch_with_correct_arguments(self) -> None:
        """Test that transcribe command passes correct arguments to process_batch.

        Feature: batch-transcribe

        The transcribe command should pass the feed URL, indices, and
        skip_language_check flag to process_batch.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock successful results
            mock_results = [
                BatchResult(index=1, success=True, output_path="/path/1.md", error_message=None),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command with skip-language-check flag
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "1", "2", "--skip-language-check"]
            )

            # Verify process_batch was called with correct arguments
            mock_process_batch.assert_called_once_with(
                feed_url="https://example.com/feed.xml",
                indices=(1, 2),
                skip_language_check=True,
            )

            # Verify display_summary was called
            mock_display_summary.assert_called_once_with(mock_results)

    def test_transcribe_calls_display_summary_with_results(self) -> None:
        """Test that transcribe command calls display_summary with results.

        Feature: batch-transcribe

        The transcribe command should call display_summary with the results
        returned from process_batch.

        **Validates: Requirements 3.5**
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from podtext.cli.main import cli

        runner = CliRunner()

        with patch("podtext.cli.main.process_batch") as mock_process_batch, \
             patch("podtext.cli.main.display_summary") as mock_display_summary:

            # Mock results with specific data
            mock_results = [
                BatchResult(index=5, success=True, output_path="/path/5.md", error_message=None),
                BatchResult(index=10, success=False, output_path=None, error_message="Test error"),
            ]
            mock_process_batch.return_value = mock_results

            # Run the command
            result = runner.invoke(
                cli,
                ["transcribe", "https://example.com/feed.xml", "5", "10"]
            )

            # Verify display_summary was called with the exact results
            mock_display_summary.assert_called_once_with(mock_results)

            # Verify the results passed to display_summary match what process_batch returned
            call_args = mock_display_summary.call_args[0][0]
            assert call_args == mock_results, (
                f"display_summary should be called with results from process_batch"
            )
