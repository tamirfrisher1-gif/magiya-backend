from telegram import Update
from telegram.ext import ContextTypes


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Pong! MAGIYA bot is alive 🎉")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Available commands:\n\n"
        "/start — Welcome message\n"
        "/ping  — Check if the bot is running\n"
        "/rsvp  — Submit your RSVP\n"
        "/seating — (Admins only) Generate AI seating plan for confirmed guests\n"
        "/stats — (Admins only) View RSVP dashboard stats"
    )
