"""Main CLI entry point for podtext."""

import click

from podtext.config.manager import ConfigManager


# Store config in context for subcommands
pass_config = click.make_pass_decorator(ConfigManager, ensure=True)


@click.group()
@click.version_option(package_name="podtext")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """podtext - Podcast discovery, transcription, and AI-powered analysis.

    Search for podcasts, list episodes, and transcribe them with AI analysis.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_manager"] = ConfigManager()


# Import and register subcommands
from podtext.cli.episodes import episodes
from podtext.cli.search import search
from podtext.cli.transcribe import transcribe

cli.add_command(search)
cli.add_command(episodes)
cli.add_command(transcribe)
