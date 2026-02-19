"""
Launch the Telegram bot.

Usage:
    python run_telegram.py          # reads token from .env
    TELEGRAM_BOT_TOKEN=xxx python run_telegram.py  # or via env var
"""

import os
import sys
from pathlib import Path

from telegram_bot import create_bot


def _load_env() -> None:
    """Load .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Error: set TELEGRAM_BOT_TOKEN in .env or environment")
        sys.exit(1)

    app = create_bot(token)
    print("Telegram bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
