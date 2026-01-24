"""CLI entry point for Podtext.

Provides commands for podcast discovery, episode listing, and transcription.

Requirements: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4
"""

from __future__ import annotations

import sys

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
@click.argument("index", type=int)
@click.option("--skip-language-check", is_flag=True, help="Skip language detection")
def transcribe(feed_url: str, index: int, skip_language_check: bool) -> None:
    """Transcribe a podcast episode.
    
    FEED_URL: URL of the podcast RSS feed.
    INDEX: Episode index number from the episodes list.
    
    Downloads the episode, transcribes it using MLX-Whisper, and generates
    a markdown file with the transcript and AI analysis.
    """
    # Import here to avoid circular imports and heavy dependencies at startup
    from pathlib import Path
    
    from podtext.core.config import ConfigError, load_config
    from podtext.services.claude import AnalysisResult, analyze_content
    from podtext.services.downloader import (
        DownloadError,
        download_with_optional_cleanup,
    )
    from podtext.services.transcriber import (
        TranscriptionError,
        transcribe as transcribe_audio,
    )
    from podtext.core.output import generate_markdown
    
    # Load configuration
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Parse feed to get episode info
    try:
        episode_list = parse_feed(feed_url, limit=index + 10)  # Get enough episodes
    except RSSFeedError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Find the episode with the specified index
    episode = None
    for ep in episode_list:
        if ep.index == index:
            episode = ep
            break
    
    if episode is None:
        click.echo(f"Error: Episode with index {index} not found.", err=True)
        sys.exit(1)
    
    click.echo(f"Transcribing: {episode.title}")
    click.echo(f"Published: {episode.pub_date.strftime('%Y-%m-%d')}")
    
    # Download media file
    click.echo("Downloading media file...")
    try:
        with download_with_optional_cleanup(episode.media_url, config) as media_path:
            click.echo(f"Downloaded to: {media_path}")
            
            # Transcribe audio
            click.echo("Transcribing audio...")
            try:
                transcription = transcribe_audio(
                    media_path,
                    model=config.whisper.model,
                    skip_language_check=skip_language_check,
                )
                click.echo(f"Transcription complete. Language: {transcription.language}")
            except TranscriptionError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
            
            # Analyze content with Claude
            click.echo("Analyzing content...")
            api_key = config.get_anthropic_key()
            analysis = analyze_content(
                transcription.text,
                api_key=api_key,
                warn_on_unavailable=True,
            )
            
            # Generate output filename
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "_"
                for c in episode.title
            )[:50]
            output_filename = f"{safe_title}.md"
            output_path = config.get_output_dir() / output_filename
            
            # Generate markdown output
            click.echo("Generating output...")
            generate_markdown(
                episode=episode,
                transcription=transcription,
                analysis=analysis,
                output_path=output_path,
            )
            
            click.echo(f"Output saved to: {output_path}")
            
    except DownloadError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
