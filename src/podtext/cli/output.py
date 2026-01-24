"""CLI output formatting utilities."""

from rich.console import Console
from rich.table import Table

from podtext.core.models import Episode, Podcast


def display_podcasts(podcasts: list[Podcast], console: Console) -> None:
    """Display podcast search results in a table."""
    if not podcasts:
        console.print("[yellow]No podcasts found.[/yellow]")
        return

    table = Table(title="Podcast Search Results")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Author", style="dim")
    table.add_column("Feed URL", style="cyan", no_wrap=True, overflow="ellipsis")

    for i, podcast in enumerate(podcasts, 1):
        table.add_row(
            str(i),
            podcast.title,
            podcast.author or "-",
            podcast.feed_url,
        )

    console.print(table)


def display_episodes(episodes: list[Episode], console: Console) -> None:
    """Display episode list in a table."""
    if not episodes:
        console.print("[yellow]No episodes found.[/yellow]")
        return

    table = Table(title="Episodes")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Title", style="bold")
    table.add_column("Published", style="green")
    table.add_column("Duration", style="cyan")

    for episode in episodes:
        duration_str = _format_duration(episode.duration) if episode.duration else "-"
        table.add_row(
            str(episode.index),
            episode.title,
            episode.published.strftime("%Y-%m-%d"),
            duration_str,
        )

    console.print(table)


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
