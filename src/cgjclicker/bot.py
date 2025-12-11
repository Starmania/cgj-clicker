"""
Energy game bot for Code Game Jam website.
Automates the clicking game at https://cgj.bpaul.fr/game/energy
"""

import asyncio
import json as json_module
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import math
import random

import httpx


def humaniser():
    x = random.uniform(0, 113)
    return 1.2 * (2.9**x + 1) / (math.exp(x) * 1.5)


def delta_to_date(date_str: str) -> timedelta:
    """
    Return the timedelta between now (UTC) and the given date.
    Positive means the given date is in the future.
    """
    target = datetime.fromisoformat(date_str)
    now = datetime.now(timezone.utc)
    return target - now


def extract_next_click_time(html: str) -> Optional[timedelta]:
    """
    Extract the next available click time from the game HTML.
    Parses the data-counter-events-value attribute.
    Returns timedelta until next click, or None if not found or available now.
    """
    # Find the counter element (handle multiline with DOTALL flag)
    match = re.search(
        r'data-controller="counter"\s+data-counter-events-value="([^"]*(?:\n[^"]*)*)"',
        html,
        re.DOTALL,
    )
    if not match:
        # No counter element means the click is available now
        return timedelta(0)

    try:
        # Get the JSON value (with HTML entities)
        json_str = match.group(1)
        # Decode HTML entities
        json_str = json_str.replace("&quot;", '"')
        # Remove newlines
        json_str = json_str.replace("\n", "")

        # Parse the JSON array
        events = json_module.loads(json_str)
        if not events or len(events) == 0:
            # No events means click is available
            return timedelta(0)

        event = events[0]

        # Calculate the timeout duration from start-date to end-date
        start_date_str = event.get("start-date")
        end_date_str = event.get("end-date")

        if not start_date_str or not end_date_str:
            # If no dates, click is available now
            return timedelta(0)

        start = datetime.fromisoformat(start_date_str)
        end = datetime.fromisoformat(end_date_str)

        # The cooldown duration is the time between start and end
        timeout_duration = end - start

        # Check if the timeout has already passed or is very small
        if timeout_duration.total_seconds() <= 0:
            return timedelta(0)

        return timeout_duration

    except (json_module.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing counter events: {e}")
        # If error, assume click is available
        return timedelta(0)


@dataclass
class GameSession:
    """Represents an authenticated game session."""

    email: str
    password: str
    base_url: str = "https://cgj.bpaul.fr"
    cookies: Optional[httpx.Cookies] = None
    client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def login(self) -> bool:
        """
        Authenticate with the game server.
        Returns True if login was successful, False otherwise.
        """
        if not self.client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )

        login_url = f"{self.base_url}/security/login"

        try:
            # Get login page to retrieve CSRF token
            response = await self.client.get(login_url)
            response.raise_for_status()

            # Extract CSRF token from the login page HTML
            csrf_match = re.search(
                r'name="_csrf_token"\s+value="([^"]*)"', response.text
            )
            csrf_token = csrf_match.group(1) if csrf_match else None

            # Prepare login data
            login_data = {
                "_username": self.email,
                "_password": self.password,
                "_remember_me": "on",
            }

            # Add CSRF token if found
            if csrf_token:
                login_data["_csrf_token"] = csrf_token

            # Submit login form
            response = await self.client.post(
                f"{self.base_url}/security/login#",
                data=login_data,
                headers={"Origin": self.base_url},
            )
            response.raise_for_status()

            # Store cookies for subsequent requests
            self.cookies = self.client.cookies

            return response.url.path != "/security/login"

        except httpx.RequestError as e:
            print(f"Login failed: {e}")
            return False

    async def click(self) -> bool:
        """
        Perform a click action on the energy game.
        Returns True if click was successful, False otherwise.
        """
        if not self.client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )

        action_url = f"{self.base_url}/game/energy/action"

        try:
            response = await self.client.post(
                action_url,
                data={},
                headers={"Origin": self.base_url},
                follow_redirects=True,
            )
            response.raise_for_status()

            return response.status_code in (200, 302)

        except httpx.RequestError as e:
            print(f"Click action failed: {e}")
            return False

    async def get_game_state(self) -> Optional[dict]:
        """
        Fetch the current game state.
        Returns game state data including next click time, if successful.
        """
        if not self.client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )

        game_url = f"{self.base_url}/game/energy"

        try:
            response = await self.client.get(game_url)
            response.raise_for_status()

            # Extract next click time from HTML
            next_click_delta = extract_next_click_time(response.text)
            next_click_seconds = (
                next_click_delta.total_seconds() if next_click_delta else None
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "url": str(response.url),
                "next_click_in_seconds": next_click_seconds,
            }

        except httpx.RequestError as e:
            print(f"Failed to fetch game state: {e}")
            return None


class EnergyBot:
    """Bot that automates the energy clicking game."""

    def __init__(
        self, email: str, password: str, base_url: str = "https://cgj.bpaul.fr"
    ):
        """Initialize the bot with credentials."""
        self.email = email
        self.password = password
        self.base_url = base_url
        self.click_count = 0
        self.session: Optional[GameSession] = None

        if not self.email or not self.password:
            raise ValueError("Email and password must be provided for the bot.")

    async def run(
        self,
        click_interval: Optional[float] = None,
        max_clicks: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """
        Run the bot clicking game.

        Args:
            click_interval: Delay between clicks in seconds. If None, uses server's dynamic timeout.
            max_clicks: Maximum number of clicks before stopping (default: None = unlimited)
            duration: Maximum duration in seconds before stopping (default: None = unlimited)
        """
        async with GameSession(
            email=self.email,
            password=self.password,
            base_url=self.base_url,
        ) as session:
            self.session = session

            # Authenticate
            print("Logging in...")
            if not await session.login():
                print("Failed to login. Aborting.")
                return

            print(f"✓ Login successful for {self.email}")

            # Get initial game state
            state = await session.get_game_state()
            if state:
                print(f"✓ Game state retrieved")
                if state.get("next_click_in_seconds") is not None:
                    next_click = state["next_click_in_seconds"]
                    if next_click > 0:
                        print(f"  Next click available in {next_click:.2f}s")

            # Start clicking loop
            if click_interval is not None:
                print(f"Starting to click (interval: {click_interval}s)...")
            else:
                print("Starting to click (using server's dynamic timeouts)...")

            start_time = asyncio.get_event_loop().time()

            try:
                while True:
                    # Check if we've reached max clicks
                    if max_clicks and self.click_count >= max_clicks:
                        print(f"Reached max clicks limit ({max_clicks})")
                        break

                    # Check if we've exceeded duration
                    if duration:
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed >= duration:
                            print(f"Reached duration limit ({duration}s)")
                            break

                    # Fetch game state to get server's dynamic timeout
                    state = await session.get_game_state()
                    server_wait_time: float = 0
                    if state and state.get("next_click_in_seconds"):
                        server_wait_time = max(0, state["next_click_in_seconds"])

                    human_delay = humaniser()
                    print(f"Humanizer delay: {human_delay:.2f}s")
                    server_wait_time += human_delay

                    # Determine wait time: use maximum of configured interval and server timeout
                    wait_time: float = server_wait_time
                    if click_interval is not None and click_interval > 0:
                        wait_time = max(wait_time, click_interval)

                    # Show waiting message if server timeout is significant
                    if server_wait_time > 1:
                        print(f"Server cooldown: {server_wait_time:.2f}s. Waiting...")

                    # Wait before clicking
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)

                    # Perform click
                    success = await session.click()
                    if success:
                        self.click_count += 1
                        if self.click_count % 10 == 0:
                            print(f"Clicks: {self.click_count}")
                    else:
                        print("Click failed, retrying...")
                        pass

            except KeyboardInterrupt:
                print("\nBot interrupted by user")

            finally:
                elapsed = asyncio.get_event_loop().time() - start_time
                print(
                    f"\nBot finished. Total clicks: {self.click_count} in {elapsed:.2f}s"
                )


async def main():
    """Example usage of the EnergyBot."""
    # Replace with actual credentials
    EMAIL = "your-email@example.com"
    PASSWORD = "your-password"

    bot = EnergyBot(email=EMAIL, password=PASSWORD)
    await bot.run(click_interval=0.5, max_clicks=100)


if __name__ == "__main__":
    asyncio.run(main())
