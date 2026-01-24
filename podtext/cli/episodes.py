"""Episodes command for listing podcast episodes."""

import click

from podtext.config.manager import ConfigManager
from podtext.services.podcast import PodcastError, PodcastService


@click.command()
@click.argument("feed_url")
@click.option(
    "-n",
    "--limit",
    default=None,
    type=int,
    help="Maximum number of episodes to show (default: from config)",
)
@click.pass_context
def episodes(ctx: click.Context, feed_url: str, limit: int | None) -> None:
    """List recent episodes from a podcast feed.

    FEED_URL should be an RSS feed URL (use 'podtext search' to find feeds).

    Examples:

        podtext episodes "https://example.com/feed.xml"

        podtext episodes "https://example.com/feed.xml" -n 20
    """
    config_manager: ConfigManager = ctx.obj["config_manager"]
    config = config_manager.load()

    # Use config default if not specified
    if limit is None:
        limit = config.episode_limit

    service = PodcastService()

    try:
        click.echo(f"Fetching episodes...\n")
        episode_list = service.get_episodes(feed_url, limit)
        podcast_name = service.get_podcast_name(feed_url)
    except PodcastError as e:
        raise click.ClickException(str(e))

    if not episode_list:
        click.echo("No episodes found.")
        return

    # Display podcast name
    click.echo(f"Podcast: {click.style(podcast_name, bold=True)}\n")
    click.echo(f"Showing {len(episode_list)} most recent episode(s):\n")

    # Display episodes with index numbers
    for i, episode in enumerate(episode_list, 1):
        date_str = episode.pub_date.strftime("%Y-%m-%d")
        duration_str = f" [{episode.duration_formatted}]" if episode.duration else ""

        click.echo(f"{i:3d}. {click.style(episode.title, bold=True)}")
        click.echo(f"     {date_str}{duration_str}")
        click.echo()

    # Show usage hint
    click.echo(f"To transcribe an episode, use:")
    click.echo(f"  podtext transcribe \"{feed_url}\" <INDEX>")
