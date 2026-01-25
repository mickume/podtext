"""CLI entry point for Podtext.

Provides commands for podcast discovery, episode listing, and transcription.

Requirements: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import click

from podtext.services.itunes import (
    ITunesAPIError,
    PodcastSearchResult,
    search_podcasts,
)
from podtext.services.rss import (
    EpisodeInfo,
    RSSFeedError,
    parse_feed,
)


@dataclass
class BatchResult:
    """Result of processing a single episode in a batch.

    Tracks the outcome of processing each episode during batch transcription,
    including success status, output file location, and error information.

    Attributes:
        index: Episode index that was processed (1-based).
        success: Whether processing succeeded.
        output_path: Path to output file if successful, None otherwise.
        error_message: Error description if failed, None otherwise.

    Validates: Requirements 3.3, 5.4
    """

    index: int
    success: bool
    output_path: str | None
    error_message: str | None


def deduplicate_indices(indices: tuple[int, ...]) -> list[int]:
    """Remove duplicate indices while preserving first occurrence order.

    When multiple indices are provided for batch processing, duplicates should
    be removed to avoid processing the same episode multiple times. The order
    of first occurrence is preserved to maintain user intent.

    Args:
        indices: Tuple of episode indices (may contain duplicates).

    Returns:
        List of unique indices in order of first occurrence.

    Example:
        >>> deduplicate_indices((1, 3, 2, 3, 1, 5))
        [1, 3, 2, 5]

    Validates: Requirements 1.3
    """
    seen: set[int] = set()
    result: list[int] = []

    for index in indices:
        if index not in seen:
            seen.add(index)
            result.append(index)

    return result


def process_batch(
    feed_url: str,
    indices: tuple[int, ...],
    skip_language_check: bool,
) -> list[BatchResult]:
    """Process multiple episodes sequentially.

    Orchestrates batch transcription by processing each episode one at a time
    in the order specified. Deduplicates indices to avoid processing the same
    episode multiple times. Displays progress information and continues
    processing even if individual episodes fail.

    Args:
        feed_url: RSS feed URL.
        indices: Episode indices to process (may contain duplicates).
        skip_language_check: If True, bypass language detection.

    Returns:
        List of BatchResult objects, one per unique episode processed.

    Validates: Requirements 2.1, 5.1
    """
    from podtext.core.config import ConfigError, load_config
    from podtext.core.pipeline import run_pipeline_safe
    from podtext.services.rss import RSSFeedError, parse_feed

    # Deduplicate indices while preserving order
    unique_indices = deduplicate_indices(indices)

    # Display initial message with total count (Requirement 5.1)
    total_count = len(unique_indices)
    click.echo(f"Processing {total_count} episode{'s' if total_count != 1 else ''} from feed...")
    click.echo()

    # Load configuration once for all episodes
    try:
        config = load_config()
    except ConfigError as e:
        # Fatal error - cannot proceed without config
        click.echo(f"Configuration error: {e}", err=True)
        return [
            BatchResult(
                index=idx,
                success=False,
                output_path=None,
                error_message=f"Configuration error: {e}",
            )
            for idx in unique_indices
        ]

    # Parse feed once to get all episodes
    try:
        # Get enough episodes to cover the maximum index
        max_index = max(unique_indices) if unique_indices else 1
        episode_list = parse_feed(feed_url, limit=max_index + 10)
    except RSSFeedError as e:
        # Fatal error - cannot proceed without feed
        click.echo(f"Feed error: {e}", err=True)
        return [
            BatchResult(
                index=idx,
                success=False,
                output_path=None,
                error_message=f"Feed error: {e}",
            )
            for idx in unique_indices
        ]

    # Create a mapping of index to episode for quick lookup
    episode_map = {ep.index: ep for ep in episode_list}

    # Process each episode sequentially (Requirement 2.1)
    results: list[BatchResult] = []

    for i, index in enumerate(unique_indices, 1):
        # Display progress indicator (Requirement 5.2)
        click.echo(f"[{i}/{total_count}] Processing episode {index}...")

        # Check if episode exists in feed
        episode = episode_map.get(index)
        if episode is None:
            error_msg = f"Episode {index} not found in feed"
            results.append(
                BatchResult(
                    index=index,
                    success=False,
                    output_path=None,
                    error_message=error_msg,
                )
            )
            click.echo(f"✗ Episode {index} failed: {error_msg}", err=True)
            click.echo()
            continue

        # Process the episode using the pipeline
        pipeline_result = run_pipeline_safe(
            episode=episode,
            config=config,
            skip_language_check=skip_language_check,
        )

        if pipeline_result is not None:
            # Success
            output_path_str = str(pipeline_result.output_path)
            results.append(
                BatchResult(
                    index=index,
                    success=True,
                    output_path=output_path_str,
                    error_message=None,
                )
            )
            click.echo(f"✓ Episode {index} transcribed successfully: {output_path_str}")
        else:
            # Failure - run_pipeline_safe already displayed error message
            error_msg = "Transcription failed (see error above)"
            results.append(
                BatchResult(
                    index=index,
                    success=False,
                    output_path=None,
                    error_message=error_msg,
                )
            )
            click.echo(f"✗ Episode {index} failed", err=True)

        click.echo()

    return results


def display_summary(results: list[BatchResult]) -> None:
    """Display summary of batch processing results.

    Shows counts of successful and failed episodes after batch processing
    completes. Provides a clear overview of the batch operation outcome.

    Args:
        results: List of BatchResult objects from batch processing.

    Validates: Requirements 3.3, 5.4
    """
    if not results:
        click.echo("No episodes were processed.")
        return

    # Count successes and failures
    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)

    # Display summary header
    click.echo()
    click.echo("Batch processing complete:")

    # Display success count
    if success_count > 0:
        click.echo(f"  ✓ {success_count} successful")

    # Display failure count
    if failure_count > 0:
        click.echo(f"  ✗ {failure_count} failed")


def format_search_results(results: list[PodcastSearchResult]) -> str:
    """Format podcast search results for display.

    Displays each result with title and feed_url.

    Args:
        results: List of podcast search results.

    Returns:
        Formatted string for display.

    Validates: Requirements 1.2
    """
    if not results:
        return "No podcasts found."

    lines: list[str] = []
    for i, result in enumerate(results, start=1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   Feed: {result.feed_url}")

    return "\n".join(lines)


def format_episode_results(episodes: list[EpisodeInfo]) -> str:
    """Format episode listing results for display.

    Displays each episode with index, title, and publication date.

    Args:
        episodes: List of episode information.

    Returns:
        Formatted string for display.

    Validates: Requirements 2.2
    """
    if not episodes:
        return "No episodes found."

    lines: list[str] = []
    for episode in episodes:
        # Format date as YYYY-MM-DD
        date_str = episode.pub_date.strftime("%Y-%m-%d")
        lines.append(f"{episode.index}. {episode.title}")
        lines.append(f"   Published: {date_str}")

    return "\n".join(lines)


@click.group()
@click.version_option(package_name="podtext")
def cli() -> None:
    """Podtext - Podcast transcription and analysis tool.

    Download podcast episodes from RSS feeds and transcribe them using
    MLX-Whisper (optimized for Apple Silicon). Uses Claude AI for
    post-processing including advertisement detection/removal and
    content analysis.
    """
    pass


@cli.command()
@click.argument("keywords", nargs=-1, required=True)
@click.option("--limit", "-n", default=10, help="Maximum number of results to display")
def search(keywords: tuple[str, ...], limit: int) -> None:
    """Search for podcasts by keywords.

    KEYWORDS: One or more search terms to find podcasts.

    Validates: Requirements 1.2, 1.3, 1.4, 1.5
    """
    query = " ".join(keywords)

    try:
        results = search_podcasts(query, limit=limit)
        output = format_search_results(results)
        click.echo(output)
    except ITunesAPIError as e:
        # Display error message and exit gracefully (Requirement 1.5)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feed_url")
@click.option("--limit", "-n", default=10, help="Maximum number of episodes to display")
def episodes(feed_url: str, limit: int) -> None:
    """List recent episodes from a podcast feed.

    FEED_URL: URL of the podcast RSS feed.

    Validates: Requirements 2.2, 2.3, 2.4, 2.5
    """
    try:
        episode_list = parse_feed(feed_url, limit=limit)
        output = format_episode_results(episode_list)
        click.echo(output)
    except RSSFeedError as e:
        # Display error message and exit gracefully (Requirement 2.5)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feed_url")
@click.argument("indices", nargs=-1, type=int, required=True)
@click.option("--skip-language-check", is_flag=True, help="Skip language detection")
def transcribe(feed_url: str, indices: tuple[int, ...], skip_language_check: bool) -> None:
    """Transcribe one or more podcast episodes.

    FEED_URL: URL of the podcast RSS feed.
    INDICES: One or more episode index numbers from the episodes list.

    Downloads the episodes, transcribes them using MLX-Whisper, and generates
    markdown files with the transcripts and AI analysis. Episodes are processed
    sequentially in the order specified.

    Validates: Requirements 1.1, 1.4, 1.5, 3.5
    """
    # Process all episodes using batch processing
    results = process_batch(
        feed_url=feed_url,
        indices=indices,
        skip_language_check=skip_language_check,
    )

    # Display summary of results
    display_summary(results)

    # Set exit code based on results (Requirement 3.5)
    # Exit code 0 if all episodes succeeded, 1 if any failures
    if any(not result.success for result in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    cli()
