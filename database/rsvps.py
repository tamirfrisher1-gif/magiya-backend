from typing import Optional
from datetime import datetime, timezone
from database.client import db


def get_rsvp_by_guest(guest_id: str) -> Optional[dict]:
    response = (
        db.table("rsvps")
        .select("*")
        .eq("guest_id", guest_id)
        .maybe_single()
        .execute()
    )
    return response.data


def upsert_rsvp(
    guest_id: str,
    status: str,
    party_size: int = 1,
    dietary_restrictions: Optional[str] = None,
) -> dict:
    payload = {
        "guest_id": guest_id,
        "status": status,
        "party_size": party_size,
        "dietary_restrictions": dietary_restrictions,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }
    response = db.table("rsvps").upsert(payload, on_conflict="guest_id").execute()
    return response.data[0]


def get_dashboard_stats() -> dict:
    """Returns counts for confirmed / declined / pending RSVPs."""
    rows = db.table("rsvps").select("status").execute().data
    stats: dict[str, int] = {"confirmed": 0, "declined": 0, "pending": 0}
    for row in rows:
        key = row["status"]
        if key in stats:
            stats[key] += 1
    return stats
