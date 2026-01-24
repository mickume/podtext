"""Search command for podcast discovery."""

import click

from podtext.clients.itunes import iTunesError
from podtext.config.manager import ConfigManager
from podtext.services.podcast import PodcastService


@click.command()
@click.argument("term")
@click.option(
    "-n",
    "--limit",
    default=None,
    type=int,
    help="Maximum number of results to show (default: from config)",
)
@click.pass_context
def search(ctx: click.Context, term: str, limit: int | None) -> None:
    """Search for podcasts matching TERM.

    Searches podcast titles, authors, and descriptions via the iTunes API.

    Examples:

        podtext search "technology news"

        podtext search "science podcast" -n 20
    """
    config_manager: ConfigManager = ctx.obj["config_manager"]
    config = config_manager.load()

    # Use config default if not specified
    if limit is None:
        limit = config.search_limit

    service = PodcastService()

    try:
        click.echo(f"Searching for '{term}'...\n")
        podcasts = service.search(term, limit)
    except iTunesError as e:
        raise click.ClickException(str(e))

    if not podcasts:
        click.echo("No podcasts found.")
        return

    # Display results
    click.echo(f"Found {len(podcasts)} podcast(s):\n")

    for i, podcast in enumerate(podcasts, 1):
        click.echo(f"{i}. {click.style(podcast.title, bold=True)}")
        if podcast.author:
            click.echo(f"   by {podcast.author}")
        click.echo(f"   Feed: {podcast.feed_url}")
        if podcast.genre:
            click.echo(f"   Genre: {podcast.genre}")
        click.echo()
