"""
Launch the Telegram bot.

Usage:
    TELEGRAM_BOT_TOKEN=xxx python run_telegram.py
"""

import os
import sys

from telegram_bot import create_bot


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Error: set TELEGRAM_BOT_TOKEN environment variable")
        sys.exit(1)

    app = create_bot(token)
    print("Telegram bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
