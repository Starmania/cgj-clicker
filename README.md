# CGJ Clicker - Energy Game Bot

A Python bot that automates the clicking game at [Code Game Jam](https://cgj.bpaul.fr/game/energy).

## Installation

```bash
cd cgjClicker
uv pip install -e .
```

## Usage

```bash
# Start the bot (uses server's dynamic timeouts)
cgjclicker start

# Or provide parameters directly
cgjclicker start \
    --email your-email@example.com \
    --password your-password \
    --max-clicks 100
```

## Options

- `--email`: Email address for authentication
- `--password`: Password for authentication
- `--max-clicks`: Maximum number of clicks before stopping
- `--duration`: Maximum duration in seconds
- `--url`: Base URL of the game server (default: https://cgj.bpaul.fr)

## Architecture

### Core Components

1. **GameSession**: Manages HTTP client and game authentication

   - Handles login flow with CSRF token extraction
   - Maintains cookies for authenticated requests
   - Provides game state queries with dynamic timeout parsing

2. **EnergyBot**: High-level bot interface

   - Orchestrates login and clicking loop
   - Respects server-imposed click cooldowns
   - Tracks statistics

3. **CLI**: Command-line interface
   - Interactive and command-line argument modes
   - User-friendly prompts and feedback

## Requirements

- Python 3.12+
- httpx 0.24.0+
- click 8.1.0+

## License

MIT
