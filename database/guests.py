from typing import Optional
from database.client import db


def get_all_guests() -> list[dict]:
    response = db.table("guests").select("*").execute()
    return response.data


def get_guest_by_phone(phone: str) -> Optional[dict]:
    response = db.table("guests").select("*").eq("phone", phone).maybe_single().execute()
    return response.data


def upsert_guest(data: dict) -> dict:
    """Insert or update a guest. `data` must include `phone` as the unique key."""
    response = db.table("guests").upsert(data, on_conflict="phone").execute()
    return response.data[0]


def delete_guest(guest_id: str) -> None:
    db.table("guests").delete().eq("id", guest_id).execute()
