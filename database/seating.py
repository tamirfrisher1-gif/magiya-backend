from database.client import db


def get_seating_plan(wedding_id: str) -> list[dict]:
    """Returns all seating assignments for a wedding, sorted by table number."""
    return (
        db.table("seating_assignments")
        .select("guest_phone, table_number")
        .eq("wedding_id", wedding_id)
        .order("table_number")
        .execute()
        .data
    )


def get_seating_by_table(wedding_id: str) -> dict[int, list[str]]:
    """Returns a dict mapping table_number → list of guest phones."""
    rows = get_seating_plan(wedding_id)
    result: dict[int, list[str]] = {}
    for row in rows:
        table = row["table_number"]
        result.setdefault(table, []).append(row["guest_phone"])
    return result


def clear_seating(wedding_id: str) -> None:
    """Deletes all seating assignments for a wedding (e.g. before re-running the algorithm)."""
    db.table("seating_assignments").delete().eq("wedding_id", wedding_id).execute()
