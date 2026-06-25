from typing import Optional
from database.client import db


def create_wedding(
    wedding_id: str,
    bride_name: str,
    groom_name: str,
    wedding_date: str,
    table_capacity: int = 10,
) -> dict:
    """Creates a new wedding record. wedding_id should be unique (e.g. 'sarah-et-david-15-08-2026')."""
    data = {
        "id": wedding_id,
        "bride_name": bride_name,
        "groom_name": groom_name,
        "wedding_date": wedding_date,
        "table_capacity": table_capacity,
    }
    response = db.table("weddings").upsert(data, on_conflict="id").execute()
    return response.data[0]


def get_wedding(wedding_id: str) -> Optional[dict]:
    """Returns the wedding record for the given id, or None if not found."""
    response = (
        db.table("weddings").select("*").eq("id", wedding_id).maybe_single().execute()
    )
    return response.data if response is not None else None
