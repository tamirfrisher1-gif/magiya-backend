from database.client import db


def _get_guests_by_group(wedding_id: str) -> dict[str, list[dict]]:
    """Fetches all guests for a wedding and groups them by group_name."""
    rows = (
        db.table("guests")
        .select("phone, full_name, group_name")
        .eq("wedding_id", wedding_id)
        .execute()
        .data
    )
    groups: dict[str, list[dict]] = {}
    for guest in rows:
        group = guest.get("group_name") or "Non assigné"
        groups.setdefault(group, []).append(guest)
    return groups


def assign_seats(wedding_id: str, table_capacity: int) -> list[dict]:
    """
    Assigns every guest for a wedding to a table.

    Strategy:
    - Guests from the same group sit together.
    - Groups are sorted largest-first so big groups get their own tables.
    - If a group is larger than one table it is split across consecutive tables.
    - Returns a list of dicts: {guest_phone, full_name, group_name, table_number}
    """
    groups = _get_guests_by_group(wedding_id)

    # Sort groups largest → smallest so big families fill complete tables first
    sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

    assignments: list[dict] = []
    current_table = 1
    seats_left = table_capacity

    for group_name, guests in sorted_groups:
        # If this group doesn't fit in remaining seats, start a fresh table
        # (skip if the table is already empty — no point moving to the next)
        if seats_left < len(guests) and seats_left < table_capacity:
            current_table += 1
            seats_left = table_capacity

        for guest in guests:
            if seats_left == 0:
                current_table += 1
                seats_left = table_capacity

            assignments.append(
                {
                    "guest_phone": guest["phone"],
                    "full_name": guest.get("full_name", ""),
                    "group_name": group_name,
                    "table_number": current_table,
                }
            )
            seats_left -= 1

    return assignments


def run_seating(wedding_id: str) -> dict:
    """
    Full pipeline: fetch wedding → assign seats → save to seating_assignments.
    Returns a summary: {total, tables_used, assignments}.
    """
    from database.weddings import get_wedding

    wedding = get_wedding(wedding_id)
    if not wedding:
        raise ValueError(f"Wedding '{wedding_id}' not found.")

    table_capacity = wedding["table_capacity"]
    assignments = assign_seats(wedding_id, table_capacity)

    if not assignments:
        return {"total": 0, "tables_used": 0, "assignments": []}

    # Save to Supabase (upsert so re-running overwrites the previous plan)
    rows = [
        {
            "wedding_id": wedding_id,
            "guest_phone": a["guest_phone"],
            "table_number": a["table_number"],
        }
        for a in assignments
    ]
    db.table("seating_assignments").upsert(
        rows, on_conflict="wedding_id,guest_phone"
    ).execute()

    tables_used = max(a["table_number"] for a in assignments)

    return {
        "total": len(assignments),
        "tables_used": tables_used,
        "assignments": assignments,
    }
