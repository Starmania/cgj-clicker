import asyncio
import os
import sys

from .bot import EnergyBot


def load_env():
    """Load environment variables from a .env file if it exists."""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, encoding="utf8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


async def main():
    """Run the bot with extracted credentials."""

    load_env()

    email = os.environ.get("CGJ_EMAIL")
    password = os.environ.get("CGJ_PASSWORD")
    server_url = os.environ.get("CGJ_URL", "https://cgj.bpaul.fr")

    min_click_interval = os.environ.get("CGJ_CLICK_INTERVAL", "0.5")
    max_clicks = os.environ.get("CGJ_MAX_CLICKS")
    duration = os.environ.get("CGJ_DURATION")

    print("=" * 60)
    print("🤖 CGJ Energy Game Bot")
    print("=" * 60)
    print(f"📧 Email: {email}")
    print(f"🎮 Server: {server_url}")
    print()

    bot = EnergyBot(email=email, password=password)

    print("Starting bot with:")
    print(f"  • {max_clicks or 'unlimited'} clicks maximum")
    print(f"  • {min_click_interval} second interval minimum between clicks")
    print(f"  • {duration or 'unlimited'} seconds maximum duration")
    print()

    await bot.run(
        click_interval=float(min_click_interval),
        max_clicks=int(max_clicks) if max_clicks else None,
        duration=int(duration) if duration else None,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
