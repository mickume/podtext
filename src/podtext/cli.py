"""Command-line interface for Podtext.

Provides commands for searching, listing episodes, and transcribing podcasts.
"""

import sys

import click

from .config import load_config
from .itunes import search_podcasts, ITunesAPIError
from .rss import parse_feed, RSSParseError
from .models import PodcastSearchResult, EpisodeInfo


@click.group()
@click.version_option()
def main():
    """Podtext - Podcast transcription and analysis tool."""
    pass


@main.command()
@click.argument("keywords", nargs=-1, required=True)
@click.option("--limit", "-n", default=10, help="Number of results to return (default: 10)")
def search(keywords: tuple[str, ...], limit: int):
    """Search for podcasts by keywords.

    Examples:
        podtext search python programming
        podtext search "software engineering" --limit 5
    """
    query = " ".join(keywords)

    try:
        results = search_podcasts(query, limit=limit)
    except ITunesAPIError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not results:
        click.echo("No podcasts found.")
        return

    click.echo(format_search_results(results))


@main.command()
@click.argument("feed_url")
@click.option("--limit", "-n", default=10, help="Number of episodes to return (default: 10)")
def episodes(feed_url: str, limit: int):
    """List recent episodes from a podcast feed.

    Examples:
        podtext episodes https://example.com/feed.xml
        podtext episodes https://example.com/feed.xml --limit 20
    """
    try:
        episode_list = parse_feed(feed_url, limit=limit)
    except RSSParseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not episode_list:
        click.echo("No episodes found.")
        return

    click.echo(format_episode_list(episode_list))


@main.command()
@click.argument("feed_url")
@click.argument("index", type=int)
@click.option("--skip-language-check", is_flag=True, help="Skip language detection warning")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def transcribe(feed_url: str, index: int, skip_language_check: bool, output: str | None):
    """Transcribe a podcast episode.

    INDEX is the episode number from the 'episodes' command.

    Examples:
        podtext transcribe https://example.com/feed.xml 1
        podtext transcribe https://example.com/feed.xml 3 --skip-language-check
    """
    # Import pipeline here to avoid circular imports
    from .pipeline import transcribe_episode, TranscriptionPipelineError

    config = load_config()

    try:
        output_path = transcribe_episode(
            feed_url=feed_url,
            index=index,
            config=config,
            skip_language_check=skip_language_check,
            output_path=output,
        )
        click.echo(f"Transcription saved to: {output_path}")
    except TranscriptionPipelineError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def format_search_results(results: list[PodcastSearchResult]) -> str:
    """Format search results for display.

    Args:
        results: List of search results.

    Returns:
        Formatted string for display.
    """
    lines = []
    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   Feed: {result.feed_url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_episode_list(episodes: list[EpisodeInfo]) -> str:
    """Format episode list for display.

    Args:
        episodes: List of episodes.

    Returns:
        Formatted string for display.
    """
    lines = []
    for episode in episodes:
        date_str = episode.pub_date.strftime("%Y-%m-%d")
        lines.append(f"{episode.index}. [{date_str}] {episode.title}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
