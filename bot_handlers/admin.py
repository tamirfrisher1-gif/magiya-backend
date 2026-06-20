from telegram import Update
from telegram.ext import ContextTypes
from database.rsvps import get_dashboard_stats


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
