from telegram import Update
from telegram.ext import ContextTypes
from database.rsvps import get_dashboard_stats, get_confirmed_guests
from database.client import db

TABLE_CAPACITY = 10  # default seats per table


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

    await update.message.reply_text(f"⏳ Generating seating plan for {len(guests)} confirmed guests...")

    try:
        # Group guests by group_name, sort largest group first
        groups: dict[str, list[dict]] = {}
        for g in guests:
            group = g.get("group_name") or "Unassigned"
            groups.setdefault(group, []).append(g)
        sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

        # Assign tables
        assignments = []
        current_table = 1
        seats_left = TABLE_CAPACITY

        for group_name, members in sorted_groups:
            if seats_left < len(members) and seats_left < TABLE_CAPACITY:
                current_table += 1
                seats_left = TABLE_CAPACITY
            for guest in members:
                if seats_left == 0:
                    current_table += 1
                    seats_left = TABLE_CAPACITY
                assignments.append({
                    "guest_phone": guest["phone"],
                    "table_number": current_table,
                })
                seats_left -= 1

        # Save to Supabase
        db.table("seating_assignments").upsert(
            assignments, on_conflict="guest_phone"
        ).execute()

        tables_used = max(a["table_number"] for a in assignments)
        await update.message.reply_text(
            f"✅ Seating plan saved!\n\n"
            f"👥 Guests assigned: {len(assignments)}\n"
            f"🪑 Tables used: {tables_used} (max {TABLE_CAPACITY} per table)"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Seating generation failed: {e}")
