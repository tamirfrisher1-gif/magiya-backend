from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from database.guests import get_guest_by_phone
from database.rsvps import upsert_rsvp

# Conversation states
PHONE, ATTENDANCE, PARTY_SIZE, DIETARY = range(4)


async def rsvp_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Let's record your RSVP!\n\nPlease send your phone number (digits only, e.g. 0501234567):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    guest = get_guest_by_phone(phone)

    if not guest:
        await update.message.reply_text(
            "Sorry, I couldn't find your number on the guest list. "
            "Please contact the wedding organizer."
        )
        return ConversationHandler.END

    context.user_data["guest"] = guest
    keyboard = [["Yes, I'm coming!", "No, I can't make it"]]
    await update.message.reply_text(
        f"Hi {guest['full_name']}! Are you coming to the wedding?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return ATTENDANCE


async def receive_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text.strip().lower()

    if "no" in answer:
        guest = context.user_data["guest"]
        upsert_rsvp(guest_id=guest["id"], status="declined")
        await update.message.reply_text(
            "Sorry to hear that! Your response has been recorded. Take care!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    context.user_data["status"] = "confirmed"
    await update.message.reply_text(
        "Great! How many guests will be coming (including yourself)?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PARTY_SIZE


async def receive_party_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        size = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a number (e.g. 2).")
        return PARTY_SIZE

    context.user_data["party_size"] = size
    keyboard = [["No dietary restrictions"]]
    await update.message.reply_text(
        "Do you have any dietary restrictions or allergies? "
        "(e.g. vegetarian, vegan, gluten-free, nut allergy)",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return DIETARY


async def receive_dietary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dietary = update.message.text.strip()
    if dietary.lower() == "no dietary restrictions":
        dietary = None

    guest = context.user_data["guest"]
    upsert_rsvp(
        guest_id=guest["id"],
        status=context.user_data["status"],
        party_size=context.user_data["party_size"],
        dietary_restrictions=dietary,
    )

    await update.message.reply_text(
        "Your RSVP is confirmed! See you at the wedding! 💍",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "RSVP cancelled. You can start again with /rsvp.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


rsvp_conversation = ConversationHandler(
    entry_points=[CommandHandler("rsvp", rsvp_start)],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        ATTENDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_attendance)],
        PARTY_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_party_size)],
        DIETARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dietary)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
