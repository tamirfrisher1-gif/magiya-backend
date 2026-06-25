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

WAITING_FOR_CODE = 0


async def import_contacts_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1 — send the Google OAuth URL and wait for the user to paste the code."""
    auth_url = get_auth_url()
    await update.message.reply_text(
        "📱 *Import your Google Contacts*\n\n"
        "1️⃣ Click the link below to connect your Google account\n"
        "2️⃣ Authorize access to your contacts\n"
        "3️⃣ Copy the code you receive and paste it here\n\n"
        f"{auth_url}",
        parse_mode="Markdown",
    )
    return WAITING_FOR_CODE


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2 — receive the OAuth code, fetch contacts, import to Supabase, reply with summary."""
    code = update.message.text.strip()

    await update.message.reply_text("⏳ Importing your contacts, please wait...")

    try:
        raw_contacts = fetch_google_contacts(code)
        guests = contacts_to_guests(raw_contacts)
        result = import_guests_from_list(guests)

        inserted = result["inserted"]
        skipped = len(result["skipped"])

        await update.message.reply_text(
            f"✅ Import complete!\n\n"
            f"👥 Imported: {inserted} contacts\n"
            f"⏭️ Skipped: {skipped} (missing or invalid phone number)\n\n"
            f"You can now classify your guests into groups."
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Something went wrong. Make sure you copied the full code correctly and try /import_contacts again."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the import flow."""
    await update.message.reply_text("Import cancelled. Type /import_contacts to try again.")
    return ConversationHandler.END


import_contacts_conversation = ConversationHandler(
    entry_points=[CommandHandler("import_contacts", import_contacts_start)],
    states={
        WAITING_FOR_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
