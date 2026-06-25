from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from core.google_contacts import get_auth_url, fetch_google_contacts, contacts_to_guests
from database.guests import import_guests_from_list

# Conversation state
AUTH_CODE = range(1)


async def import_contacts_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    auth_url = get_auth_url()
    await update.message.reply_text(
        "Let's import your Google Contacts!\n\n"
        f"1. Open this link and sign in:\n{auth_url}\n\n"
        "2. After granting access, copy the authorization code shown and paste it here."
    )
    return AUTH_CODE


async def receive_auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip()

    try:
        raw_contacts = fetch_google_contacts(code)
    except Exception:
        await update.message.reply_text(
            "That code didn't work. Run /import_contacts to try again."
        )
        return ConversationHandler.END

    guests = contacts_to_guests(raw_contacts)
    result = import_guests_from_list(guests)

    await update.message.reply_text(
        f"Done! Imported {result['inserted']} contacts.\n"
        f"Skipped {len(result['skipped'])} (missing or invalid phone numbers)."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Contact import cancelled. Run /import_contacts to try again.")
    return ConversationHandler.END


import_contacts_conversation = ConversationHandler(
    entry_points=[CommandHandler("import_contacts", import_contacts_start)],
    states={
        AUTH_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_code)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
