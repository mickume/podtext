"""Transcribe command for downloading and processing episodes."""

import click

from podtext.clients.claude import ClaudeError
from podtext.config.manager import ConfigManager
from podtext.output.markdown import MarkdownWriter
from podtext.services.analyzer import AnalyzerService
from podtext.services.podcast import PodcastError, PodcastService
from podtext.services.transcriber import TranscriberService, TranscriptionError


@click.command()
@click.argument("feed_url")
@click.argument("index", type=int)
@click.option(
    "--skip-language-check",
    is_flag=True,
    help="Skip language verification (transcribe regardless of detected language)",
)
@click.option(
    "--skip-analysis",
    is_flag=True,
    help="Skip AI analysis (transcription only)",
)
@click.option(
    "-n",
    "--limit",
    default=None,
    type=int,
    help="Episode limit used when listing (for index mapping)",
)
@click.pass_context
def transcribe(
    ctx: click.Context,
    feed_url: str,
    index: int,
    skip_language_check: bool,
    skip_analysis: bool,
    limit: int | None,
) -> None:
    """Transcribe a podcast episode.

    FEED_URL is the RSS feed URL.
    INDEX is the episode number from 'podtext episodes' output.

    Examples:

        podtext transcribe "https://example.com/feed.xml" 1

        podtext transcribe "https://example.com/feed.xml" 3 --skip-analysis
    """
    config_manager: ConfigManager = ctx.obj["config_manager"]
    config = config_manager.load()

    # Use config default if not specified
    if limit is None:
        limit = config.episode_limit

    # Initialize services
    podcast_service = PodcastService()
    transcriber = TranscriberService(config)
    writer = MarkdownWriter(config)

    # Get the episode
    try:
        click.echo("Fetching episode information...")
        episode = podcast_service.get_episode_by_index(feed_url, index, limit)
        podcast_name = podcast_service.get_podcast_name(feed_url)
    except PodcastError as e:
        raise click.ClickException(str(e))

    click.echo(f"Episode: {click.style(episode.title, bold=True)}")
    click.echo(f"Podcast: {podcast_name}")
    click.echo()

    # Download media
    try:
        click.echo("Downloading media file...")
        media_path = transcriber.download_media(episode.media_url)
        click.echo(f"Downloaded to: {media_path}")
    except TranscriptionError as e:
        raise click.ClickException(str(e))

    # Check language
    if not skip_language_check:
        detected_lang = episode.language or "en"
        if detected_lang != "en":
            click.echo(
                click.style(
                    f"Warning: Episode language is '{detected_lang}', not English. "
                    "Transcription quality may vary.",
                    fg="yellow",
                )
            )
            click.echo("Use --skip-language-check to suppress this warning.")
            click.echo()

    # Transcribe
    try:
        click.echo("Transcribing audio (this may take a while)...")
        transcript = transcriber.transcribe(media_path)
        click.echo(f"Transcription complete: {transcript.word_count} words")
    except TranscriptionError as e:
        transcriber.cleanup_media(media_path)
        raise click.ClickException(str(e))

    # Analyze
    analysis = None
    if not skip_analysis:
        # Check if API key is available
        if not config.get_api_key():
            click.echo(
                click.style(
                    "Warning: No Claude API key configured. Skipping analysis.",
                    fg="yellow",
                )
            )
        else:
            try:
                click.echo("Analyzing transcript with Claude AI...")
                analyzer = AnalyzerService(config)
                analysis = analyzer.analyze(transcript)
                click.echo("Analysis complete.")
            except ClaudeError as e:
                click.echo(
                    click.style(f"Warning: Analysis failed: {e}", fg="yellow")
                )
                click.echo("Continuing without analysis...")

    # Write output
    try:
        click.echo("Writing markdown file...")
        output_path = writer.write(podcast_name, episode, transcript, analysis)
        click.echo()
        click.echo(click.style("Success!", fg="green", bold=True))
        click.echo(f"Output: {output_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")
    finally:
        # Cleanup media
        transcriber.cleanup_media(media_path)

    # Show summary
    if analysis:
        click.echo()
        click.echo("Summary:")
        # Show first 200 chars of summary
        summary_preview = analysis.summary[:200]
        if len(analysis.summary) > 200:
            summary_preview += "..."
        click.echo(f"  {summary_preview}")

        if analysis.keywords:
            click.echo()
            click.echo(f"Keywords: {', '.join(analysis.keywords[:10])}")
