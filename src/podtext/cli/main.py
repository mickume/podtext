"""Main CLI application for podtext."""

from datetime import UTC
from typing import Annotated

import typer
from rich.console import Console

from podtext.core.config import Config, Verbosity

app = typer.Typer(
    name="podtext",
    help="A command-line podcast transcription and analysis tool.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


class State:
    """Global CLI state."""

    def __init__(self) -> None:
        self.verbosity: Verbosity = Verbosity.NORMAL
        self.config: Config | None = None


state = State()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from podtext import __version__

        console.print(f"podtext version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress all output except errors"),
    ] = False,
    error_only: Annotated[
        bool,
        typer.Option("--error-only", help="Show only error messages"),
    ] = False,
    config_path: Annotated[
        str | None,
        typer.Option("--config", help="Path to configuration file"),
    ] = None,
    version: Annotated[  # noqa: ARG001
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version"),
    ] = False,
) -> None:
    """podtext - Podcast transcription and analysis tool."""
    # Determine verbosity level
    if quiet:
        state.verbosity = Verbosity.QUIET
    elif error_only:
        state.verbosity = Verbosity.ERROR
    elif verbose:
        state.verbosity = Verbosity.VERBOSE
    else:
        state.verbosity = Verbosity.NORMAL

    # Load configuration
    state.config = Config.load(config_path)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search term for finding podcasts")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of results"),
    ] = 10,
) -> None:
    """Search for podcasts using the iTunes API."""
    from podtext.cli.output import display_podcasts
    from podtext.services.discovery import DiscoveryService

    if state.verbosity != Verbosity.QUIET:
        console.print(f"Searching for podcasts: [bold]{query}[/bold]")

    service = DiscoveryService()
    podcasts = service.search_podcasts(query, limit=limit)

    if state.verbosity != Verbosity.QUIET:
        display_podcasts(podcasts, console)


@app.command()
def episodes(
    feed_url: Annotated[str, typer.Argument(help="RSS feed URL of the podcast")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of episodes to show"),
    ] = 10,
) -> None:
    """List episodes from a podcast RSS feed."""
    from podtext.cli.output import display_episodes
    from podtext.services.discovery import DiscoveryService

    if state.verbosity != Verbosity.QUIET:
        console.print(f"Fetching episodes from: [bold]{feed_url}[/bold]")

    service = DiscoveryService()
    eps = service.get_episodes(feed_url, limit=limit)

    if state.verbosity != Verbosity.QUIET:
        display_episodes(eps, console)


@app.command()
def process(
    feed_url: Annotated[str, typer.Argument(help="RSS feed URL of the podcast")],
    index: Annotated[int, typer.Argument(help="Episode index (1 = most recent)")],
    skip_language_check: Annotated[
        bool,
        typer.Option("--skip-language-check", help="Skip English language verification"),
    ] = False,
    keep_media: Annotated[
        bool,
        typer.Option("--keep-media", help="Keep downloaded media files after processing"),
    ] = False,
    output_dir: Annotated[
        str | None,
        typer.Option("--output-dir", "-o", help="Output directory for transcripts"),
    ] = None,
) -> None:
    """Download, transcribe, and analyze a podcast episode."""
    from pathlib import Path

    from rich.progress import Progress, SpinnerColumn, TextColumn

    from podtext.core.errors import PodtextError
    from podtext.services.analysis import AnalysisService
    from podtext.services.discovery import DiscoveryService
    from podtext.services.download import DownloadService
    from podtext.services.output import OutputService
    from podtext.services.transcribe import TranscriptionService

    assert state.config is not None

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=state.verbosity == Verbosity.QUIET,
        ) as progress:
            # Step 1: Get episode info
            task = progress.add_task("Fetching episode info...", total=None)
            discovery = DiscoveryService()
            eps = discovery.get_episodes(feed_url, limit=index)
            if index > len(eps):
                error_console.print(f"[red]Error: Episode index {index} not found[/red]")
                raise typer.Exit(1)
            episode = eps[index - 1]
            podcast_title = discovery.get_podcast_title(feed_url)
            progress.update(task, description=f"Found: {episode.title}")

            # Step 2: Download media
            progress.update(task, description="Downloading media...")
            download_dir = Path(state.config.general.download_dir)
            download_service = DownloadService(download_dir)
            media_path = download_service.download(episode)

            # Step 3: Extract audio if needed
            progress.update(task, description="Processing audio...")
            audio_path = download_service.extract_audio(media_path)

            # Step 4: Transcribe
            progress.update(task, description="Transcribing audio...")
            transcribe_service = TranscriptionService(
                model=state.config.transcription.whisper_model,
                skip_language_check=skip_language_check
                or state.config.transcription.skip_language_check,
            )
            transcript = transcribe_service.transcribe(audio_path)

            if state.verbosity == Verbosity.VERBOSE:
                console.print(f"Detected language: {transcript.language}")

            # Step 5: Analyze with Claude
            progress.update(task, description="Analyzing transcript...")
            analysis_service = AnalysisService.from_config(state.config)
            analysis = analysis_service.analyze(transcript)

            # Step 6: Generate output
            progress.update(task, description="Generating output...")
            out_dir = Path(output_dir) if output_dir else Path(state.config.general.output_dir)
            output_service = OutputService(out_dir)

            from podtext.core.models import EpisodeOutput

            output_data = EpisodeOutput(
                podcast_title=podcast_title,
                episode=episode,
                transcript=transcript,
                analysis=analysis,
            )
            output_path = output_service.generate(output_data)

            # Step 7: Cleanup
            if not keep_media and not state.config.general.keep_media:
                progress.update(task, description="Cleaning up...")
                download_service.cleanup(media_path)
                if audio_path != media_path:
                    download_service.cleanup(audio_path)

            progress.update(task, description="[green]Complete![/green]")

        if state.verbosity != Verbosity.QUIET:
            console.print(f"\n[green]Transcript saved to:[/green] {output_path}")

    except PodtextError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def reprocess(
    media_file: Annotated[str, typer.Argument(help="Path to local media file")],
    podcast_title: Annotated[
        str,
        typer.Option("--podcast-title", "-p", help="Podcast title for output"),
    ] = "Unknown Podcast",
    episode_title: Annotated[
        str,
        typer.Option("--episode-title", "-e", help="Episode title for output"),
    ] = "Unknown Episode",
    skip_language_check: Annotated[
        bool,
        typer.Option("--skip-language-check", help="Skip English language verification"),
    ] = False,
    output_dir: Annotated[
        str | None,
        typer.Option("--output-dir", "-o", help="Output directory for transcripts"),
    ] = None,
) -> None:
    """Re-process a local media file through transcription and analysis."""
    from datetime import datetime
    from pathlib import Path

    from rich.progress import Progress, SpinnerColumn, TextColumn

    from podtext.core.errors import PodtextError
    from podtext.core.models import Episode, EpisodeOutput
    from podtext.services.analysis import AnalysisService
    from podtext.services.download import DownloadService
    from podtext.services.output import OutputService
    from podtext.services.transcribe import TranscriptionService

    assert state.config is not None

    media_path = Path(media_file)
    if not media_path.exists():
        error_console.print(f"[red]Error:[/red] File not found: {media_file}")
        raise typer.Exit(1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=state.verbosity == Verbosity.QUIET,
        ) as progress:
            task = progress.add_task("Processing...", total=None)

            # Create a dummy episode for metadata
            episode = Episode(
                index=1,
                title=episode_title,
                published=datetime.now(UTC),
                media_url=str(media_path),
            )

            # Extract audio if needed
            progress.update(task, description="Processing audio...")
            download_service = DownloadService(media_path.parent)
            audio_path = download_service.extract_audio(media_path)

            # Transcribe
            progress.update(task, description="Transcribing audio...")
            transcribe_service = TranscriptionService(
                model=state.config.transcription.whisper_model,
                skip_language_check=skip_language_check
                or state.config.transcription.skip_language_check,
            )
            transcript = transcribe_service.transcribe(audio_path)

            # Analyze
            progress.update(task, description="Analyzing transcript...")
            analysis_service = AnalysisService.from_config(state.config)
            analysis = analysis_service.analyze(transcript)

            # Generate output
            progress.update(task, description="Generating output...")
            out_dir = Path(output_dir) if output_dir else Path(state.config.general.output_dir)
            output_service = OutputService(out_dir)

            output_data = EpisodeOutput(
                podcast_title=podcast_title,
                episode=episode,
                transcript=transcript,
                analysis=analysis,
            )
            output_path = output_service.generate(output_data)

            # Cleanup extracted audio if different from source
            if audio_path != media_path:
                download_service.cleanup(audio_path)

            progress.update(task, description="[green]Complete![/green]")

        if state.verbosity != Verbosity.QUIET:
            console.print(f"\n[green]Transcript saved to:[/green] {output_path}")

    except PodtextError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
