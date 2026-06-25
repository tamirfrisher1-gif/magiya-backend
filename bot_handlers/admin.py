from telegram import Update
from telegram.ext import ContextTypes
from database.rsvps import get_dashboard_stats, get_confirmed_guests
from database.guests import get_all_guest_groups
from core.seating_algorithm import generate_seating_plan, apply_seating_plan


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_dashboard_stats()
    total = sum(data.values())
    await update.message.reply_text(
        "📊 RSVP Dashboard\n\n"
        f"Confirmed:  {data['confirmed']}\n"
        f"Declined:   {data['declined']}\n"
        f"Pending:    {data['pending']}\n"
        f"Total:      {total}"
    )


async def seating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    guests = get_confirmed_guests()
    if not guests:
        await update.message.reply_text("No confirmed guests yet — nothing to seat.")
        return

    groups = get_all_guest_groups()
    await update.message.reply_text(f"Generating seating plan for {len(guests)} confirmed guests...")

    try:
        assignments = generate_seating_plan(guests, groups)
        result = apply_seating_plan(assignments)
    except Exception as e:
        await update.message.reply_text(f"Seating generation failed: {e}")
        return

    await update.message.reply_text(
        f"Seating plan saved! {result['saved']} guests assigned across {result['tables_used']} tables."
    )
