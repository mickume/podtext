"""Command-line interface for Podtext."""

import asyncio
import sys
from pathlib import Path

import click

from podtext.config import load_config, get_anthropic_api_key
from podtext.itunes import ITunesAPIError, format_search_results, search_podcasts
from podtext.rss import RSSParseError, format_episodes, get_episode_by_index, parse_feed


@click.group()
@click.version_option()
def main() -> None:
    """Podtext - Podcast transcription and analysis tool.

    Download podcast episodes and transcribe them using MLX-Whisper,
    with optional Claude AI analysis for advertisement detection and content summaries.
    """
    pass


@main.command()
@click.argument("keywords", nargs=-1, required=True)
@click.option(
    "--limit", "-n",
    default=10,
    type=int,
    help="Maximum number of results to display (default: 10)",
)
def search(keywords: tuple[str, ...], limit: int) -> None:
    """Search for podcasts by keywords.

    Returns matching podcasts with their titles and RSS feed URLs.

    Example: podtext search python programming
    """
    query = " ".join(keywords)

    try:
        results = asyncio.run(search_podcasts(query, limit=limit))
        output = format_search_results(results)
        click.echo(output)
    except ITunesAPIError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("feed_url")
@click.option(
    "--limit", "-n",
    default=10,
    type=int,
    help="Maximum number of episodes to display (default: 10)",
)
def episodes(feed_url: str, limit: int) -> None:
    """List recent episodes from a podcast feed.

    Displays episode titles, publication dates, and index numbers.

    Example: podtext episodes https://example.com/feed.xml
    """
    try:
        episode_list = asyncio.run(parse_feed(feed_url, limit=limit))
        output = format_episodes(episode_list)
        click.echo(output)
    except RSSParseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("feed_url")
@click.argument("index", type=int)
@click.option(
    "--skip-language-check",
    is_flag=True,
    help="Skip language detection warning for non-English content",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (default: auto-generated in output directory)",
)
def transcribe(
    feed_url: str,
    index: int,
    skip_language_check: bool,
    output: str | None,
) -> None:
    """Transcribe a podcast episode.

    Downloads the episode, transcribes using MLX-Whisper, and optionally
    analyzes with Claude AI for advertisement detection and content summary.

    Example: podtext transcribe https://example.com/feed.xml 1
    """
    from podtext.pipeline import run_transcription_pipeline

    try:
        # Load configuration
        config = load_config()

        # Run the transcription pipeline
        output_path = asyncio.run(
            run_transcription_pipeline(
                feed_url=feed_url,
                episode_index=index,
                config=config,
                skip_language_check=skip_language_check,
                output_path=Path(output) if output else None,
            )
        )

        click.echo(f"Transcription complete: {output_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
