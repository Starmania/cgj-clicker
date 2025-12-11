"""
CLI interface for the Energy Game Bot.
"""

import asyncio
import sys
from pathlib import Path

import click

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cgjclicker.bot import EnergyBot


@click.group()
def cli():
    """CGJ Energy Game Bot - Automate the clicking game."""
    pass


@cli.command()
@click.option(
    "--email",
    prompt="Email",
    help="Email address for authentication",
)
@click.option(
    "--password",
    prompt="Password",
    hide_input=True,
    help="Password for authentication",
)
@click.option(
    "--interval",
    type=float,
    default=None,
    help="Delay between clicks in seconds (default: use server's dynamic timeouts)",
)
@click.option(
    "--max-clicks",
    type=int,
    default=None,
    help="Maximum number of clicks (default: unlimited)",
)
@click.option(
    "--duration",
    type=int,
    default=None,
    help="Maximum duration in seconds (default: unlimited)",
)
@click.option(
    "--url",
    default="https://cgj.bpaul.fr",
    help="Base URL of the game server",
)
def start(
    email: str, password: str, interval: float, max_clicks: int, duration: int, url: str
):
    """Start the energy game bot."""
    click.echo("🤖 Starting Energy Game Bot")
    click.echo(f"📍 Server: {url}")

    bot = EnergyBot(email=email, password=password, base_url=url)

    try:
        asyncio.run(
            bot.run(click_interval=interval, max_clicks=max_clicks, duration=duration)
        )
    except KeyboardInterrupt:
        click.echo("\n⚠️ Bot interrupted")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def info():
    """Show bot information."""
    click.echo("CGJ Energy Game Bot")
    click.echo("=" * 40)
    click.echo("A bot that automates clicking in the")
    click.echo("Code Game Jam energy game.")
    click.echo()
    click.echo("Features:")
    click.echo("  • Automated login")
    click.echo("  • Continuous clicking with configurable interval")
    click.echo("  • Limits: max clicks or duration")
    click.echo()
    click.echo("Usage: cgjclicker start")


if __name__ == "__main__":
    cli()
