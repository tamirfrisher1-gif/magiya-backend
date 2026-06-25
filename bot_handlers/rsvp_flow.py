from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from database.guests import get_guest_by_phone, get_guest_by_id
from database.rsvps import upsert_rsvp
from core.wedding_config import COUPLE_NAME_1, COUPLE_NAME_2

# Conversation states
PHONE, ATTENDANCE, GUEST_COUNT, DIETARY = range(4)

GUEST_NOT_FOUND_MSG = "מצטערים, לא מצאנו הזמנה במערכת. אנא צרו קשר עם המארגנים."


def _attendance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ אני מאשר", callback_data="attend_yes"),
            InlineKeyboardButton("❌ לא מאשר", callback_data="attend_no"),
        ]
    ])


def _guest_count_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1", callback_data="count_1"),
            InlineKeyboardButton("2", callback_data="count_2"),
            InlineKeyboardButton("3", callback_data="count_3"),
            InlineKeyboardButton("4", callback_data="count_4"),
            InlineKeyboardButton("5+", callback_data="count_5plus"),
        ]
    ])


def _dietary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("צמחוני", callback_data="diet_vegetarian")],
        [InlineKeyboardButton("טבעוני", callback_data="diet_vegan")],
        [InlineKeyboardButton("גלאט", callback_data="diet_kosher")],
        [InlineKeyboardButton("צליאקי", callback_data="diet_celiac")],
        [InlineKeyboardButton("אין", callback_data="diet_none")],
    ])


async def _send_attendance_prompt(message) -> None:
    await message.reply_text(
        f"שלום! הוזמנת לחתונה של {COUPLE_NAME_1} ו{COUPLE_NAME_2}.",
        reply_markup=_attendance_keyboard(),
    )


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /start. With a deep-link payload (?start=<guest_id>) it jumps
    straight into the RSVP flow; without one it just shows a generic welcome."""
    if not context.args:
        await update.message.reply_text(
            "ברוכים הבאים ל-MAGIYA! 💍\nלאישור הגעה הקלידו /rsvp"
        )
        return ConversationHandler.END

    guest_id = context.args[0]
    guest = get_guest_by_id(guest_id)

    if not guest:
        await update.message.reply_text(GUEST_NOT_FOUND_MSG)
        return ConversationHandler.END

    context.user_data["guest"] = guest
    await _send_attendance_prompt(update.message)
    return ATTENDANCE


async def rsvp_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /rsvp — manual flow that asks for a phone number first."""
    await update.message.reply_text("לאישור הגעה, אנא שלחו את מספר הטלפון שלכם:")
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    guest = get_guest_by_phone(phone)

    if not guest:
        await update.message.reply_text(GUEST_NOT_FOUND_MSG)
        return ConversationHandler.END

    context.user_data["guest"] = guest
    await _send_attendance_prompt(update.message)
    return ATTENDANCE


async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    guest = context.user_data["guest"]

    if query.data == "attend_no":
        upsert_rsvp(guest_id=guest["id"], status="declined")
        await query.edit_message_text("תודה שעדכנת אותנו. נשמח לראותך בהזדמנות אחרת! 💔")
        return ConversationHandler.END

    await query.edit_message_text("כמה אנשים תהיו?", reply_markup=_guest_count_keyboard())
    return GUEST_COUNT


async def handle_guest_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    raw = query.data.removeprefix("count_")
    party_size = 5 if raw == "5plus" else int(raw)
    context.user_data["party_size"] = party_size

    await query.edit_message_text("העדפות מזון:", reply_markup=_dietary_keyboard())
    return DIETARY


async def handle_dietary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    diet_map = {
        "diet_vegetarian": "צמחוני",
        "diet_vegan": "טבעוני",
        "diet_kosher": "גלאט",
        "diet_celiac": "צליאקי",
        "diet_none": None,
    }
    dietary = diet_map[query.data]
    guest = context.user_data["guest"]

    upsert_rsvp(
        guest_id=guest["id"],
        status="confirmed",
        party_size=context.user_data["party_size"],
        dietary_restrictions=dietary,
    )

    await query.edit_message_text("תודה! ה-RSVP שלך נקלט בהצלחה 🎉\nמצפים לראותך בחתונה! 💍")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("האישור בוטל. ניתן להתחיל מחדש עם /rsvp")
    return ConversationHandler.END


rsvp_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("start", start_entry),
        CommandHandler("rsvp", rsvp_start),
    ],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        ATTENDANCE: [CallbackQueryHandler(handle_attendance, pattern="^attend_")],
        GUEST_COUNT: [CallbackQueryHandler(handle_guest_count, pattern="^count_")],
        DIETARY: [CallbackQueryHandler(handle_dietary, pattern="^diet_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
