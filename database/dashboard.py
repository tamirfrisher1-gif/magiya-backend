"""Database orchestration for the dashboard: fetch rows, delegate to pure logic."""
from database.guests import get_all_guests
from database.rsvps import get_all_rsvps
from core.dashboard import build_dashboard, build_confirmed_guests


def get_dashboard_data(wedding_id: str | None = None) -> dict:
    """Fetch guests + rsvps from Supabase (filtered by wedding) and aggregate for the dashboard."""
    guests = get_all_guests(wedding_id)
    guest_ids = [g["id"] for g in guests] if wedding_id else None
    rsvps = get_all_rsvps(guest_ids)
    return build_dashboard(guests, rsvps)


def get_confirmed_guests(wedding_id: str | None = None) -> list[dict]:
    """Fetch confirmed guests for the seating page, filtered by wedding."""
    guests = get_all_guests(wedding_id)
    guest_ids = [g["id"] for g in guests] if wedding_id else None
    rsvps = get_all_rsvps(guest_ids)
    return build_confirmed_guests(guests, rsvps)
