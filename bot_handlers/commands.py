from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to MAGIYA! 💍\n\n"
        "I'm your smart wedding guest management bot.\n"
        "Use /help to see what I can do."
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Pong! MAGIYA bot is alive 🎉")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Available commands:\n\n"
        "/start — Welcome message\n"
        "/ping  — Check if the bot is running\n"
        "/rsvp  — Submit your RSVP\n"
        "/stats — (Admins only) View RSVP dashboard stats"
    )
