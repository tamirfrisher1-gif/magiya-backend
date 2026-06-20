from database.client import db


def get_all_groups() -> list[dict]:
    return db.table("seating_groups").select("*").execute().data


def create_group(group_name: str, table_number: int) -> dict:
    response = (
        db.table("seating_groups")
        .insert({"group_name": group_name, "table_number": table_number})
        .execute()
    )
    return response.data[0]


def assign_guest_to_group(guest_id: str, group_id: str, seat_number: int) -> dict:
    response = (
        db.table("seating_assignments")
        .upsert(
            {"guest_id": guest_id, "group_id": group_id, "seat_number": seat_number},
            on_conflict="guest_id",
        )
        .execute()
    )
    return response.data[0]


def get_full_seating_plan() -> list[dict]:
    """Returns all assignments joined with guest names and group info."""
    return (
        db.table("seating_assignments")
        .select("*, guests(full_name, phone), seating_groups(group_name, table_number)")
        .execute()
        .data
    )
