"""
Generates a personal Telegram deep link for every guest in Supabase and saves
them to invite_links.csv. Send each link to the matching guest via WhatsApp —
when they tap it and press "Start" in Telegram, the bot automatically begins
their RSVP flow (no need to type a phone number).

Run with: python scripts/generate_invite_links.py
"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Bot
from config.settings import TELEGRAM_BOT_TOKEN
from database.guests import get_all_guests

OUTPUT_FILE = "invite_links.csv"


async def main() -> None:
    bot = Bot(TELEGRAM_BOT_TOKEN)
    me = await bot.get_me()
    guests = get_all_guests()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["full_name", "phone", "invite_link"])
        for guest in guests:
            link = f"https://t.me/{me.username}?start={guest['id']}"
            writer.writerow([guest["full_name"], guest["phone"], link])

    print(f"Saved {len(guests)} invite links to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
