"""Database orchestration for the dashboard: fetch rows, delegate to pure logic."""
from database.guests import get_all_guests
from database.rsvps import get_all_rsvps
from core.dashboard import build_dashboard, build_confirmed_guests


def get_dashboard_data() -> dict:
    """Fetch all guests + rsvps from Supabase and aggregate them for the dashboard."""
    guests = get_all_guests()
    rsvps = get_all_rsvps()
    return build_dashboard(guests, rsvps)


def get_confirmed_guests() -> list[dict]:
    """Fetch guests + rsvps and return the confirmed guests for the seating page."""
    guests = get_all_guests()
    rsvps = get_all_rsvps()
    return build_confirmed_guests(guests, rsvps)
