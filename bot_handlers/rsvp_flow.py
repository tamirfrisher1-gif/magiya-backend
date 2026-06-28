import base64
import io
from pathlib import Path
from telegram import InputFile, Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from database.weddings import get_wedding
from core.wedding_config import COUPLE_NAME_1, COUPLE_NAME_2

# Conversation states
PHONE, ATTENDANCE, GUEST_COUNT, DIETARY = range(4)

GUEST_NOT_FOUND_MSG = "מצטערים, לא מצאנו הזמנה במערכת. אנא צרו קשר עם המארגנים."
INVITATION_IMAGE_PATH = Path(__file__).resolve().parent.parent / "assets" / "invitation.png"


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


async def _send_attendance_prompt(message, wedding: dict | None = None) -> None:
    w = wedding or {}
    name1 = w.get("bride_name") or COUPLE_NAME_1
    name2 = w.get("groom_name") or COUPLE_NAME_2
    default_text = f"שלום! הוזמנת לחתונה של {name1} ו{name2}."
    greeting = w.get("invitation_text") or default_text
    image_url = w.get("invitation_image_url")

    if image_url:
        if image_url.startswith("data:image"):
            _, b64data = image_url.split(",", 1)
            photo_bytes = io.BytesIO(base64.b64decode(b64data))
            photo_src = InputFile(photo_bytes, filename="invitation.jpg")
        else:
            photo_src = image_url
        await message.reply_photo(
            photo=photo_src,
            caption=greeting,
            reply_markup=_attendance_keyboard(),
        )
    elif INVITATION_IMAGE_PATH.exists():
        with open(INVITATION_IMAGE_PATH, "rb") as photo:
            await message.reply_photo(
                photo=photo,
                caption=greeting,
                reply_markup=_attendance_keyboard(),
            )
    else:
        await message.reply_text(greeting, reply_markup=_attendance_keyboard())


async def _advance(query, text: str, reply_markup=None) -> None:
    """Moves the conversation to its next question. The greeting may have been sent
    as a photo (with the invitation image) — Telegram can't edit a photo message into
    a text message, so in that case we drop its buttons and send a fresh text message."""
    if query.message.photo:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(text, reply_markup=reply_markup)


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

    wedding = get_wedding(guest.get("wedding_id", "")) if guest.get("wedding_id") else None
    context.user_data["guest"] = guest
    context.user_data["wedding"] = wedding
    await _send_attendance_prompt(update.message, wedding)
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

    wedding = get_wedding(guest.get("wedding_id", "")) if guest.get("wedding_id") else None
    context.user_data["guest"] = guest
    context.user_data["wedding"] = wedding
    await _send_attendance_prompt(update.message, wedding)
    return ATTENDANCE


async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    guest = context.user_data["guest"]

    if query.data == "attend_no":
        upsert_rsvp(guest_id=guest["id"], status="declined")
        await _advance(query, "תודה שעדכנת אותנו. נשמח לראותך בהזדמנות אחרת! 💔")
        return ConversationHandler.END

    await _advance(query, "כמה אנשים תהיו?", reply_markup=_guest_count_keyboard())
    return GUEST_COUNT


async def handle_guest_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    raw = query.data.removeprefix("count_")
    party_size = 5 if raw == "5plus" else int(raw)
    context.user_data["party_size"] = party_size
    context.user_data["dietary_list"] = []
    context.user_data["current_person"] = 1

    await _ask_dietary_for_current_person(query, context)
    return DIETARY


async def _ask_dietary_for_current_person(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    party_size = context.user_data["party_size"]
    person = context.user_data["current_person"]

    prompt = "העדפות מזון:" if party_size == 1 else f"העדפות מזון לאדם {person} מתוך {party_size}:"
    await query.edit_message_text(prompt, reply_markup=_dietary_keyboard())


async def handle_dietary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    diet_map = {
        "diet_vegetarian": "צמחוני",
        "diet_vegan": "טבעוני",
        "diet_kosher": "גלאט",
        "diet_celiac": "צליאקי",
        "diet_none": "אין",
    }
    context.user_data["dietary_list"].append(diet_map[query.data])
    context.user_data["current_person"] += 1

    party_size = context.user_data["party_size"]
    if context.user_data["current_person"] <= party_size:
        await _ask_dietary_for_current_person(query, context)
        return DIETARY

    dietary_list = context.user_data["dietary_list"]
    if party_size == 1:
        dietary_summary = dietary_list[0] if dietary_list[0] != "אין" else None
    else:
        dietary_summary = "\n".join(
            f"אדם {i}: {diet}" for i, diet in enumerate(dietary_list, start=1)
        )

    guest = context.user_data["guest"]
    upsert_rsvp(
        guest_id=guest["id"],
        status="confirmed",
        party_size=party_size,
        dietary_restrictions=dietary_summary,
    )

    await query.edit_message_text(
        f"תודה על אישור ההגעה, {guest['full_name']}! 🎉\nנתראה באירוע! 💍"
    )
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
