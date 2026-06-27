"""
MAGIYA Dashboard API.

A small FastAPI service that exposes aggregated guest/RSVP statistics as JSON,
so the frontend can build the dashboard UX/UI on top of a stable contract.

Run locally:
    uvicorn api.main:app --reload --port 8001

Interactive schema/docs: http://localhost:8001/docs
"""
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database.dashboard import get_dashboard_data, get_confirmed_guests
from database.guests import import_guests_from_list
from core.google_contacts import get_auth_url, fetch_google_contacts, contacts_to_guests
from config.settings import FRONTEND_GUESTLIST_URL

app = FastAPI(
    title="MAGIYA Dashboard API",
    version="1.0",
    description="Aggregated guest & RSVP statistics for the MAGIYA wedding dashboard.",
)

# Open CORS for the course project. Lock this down to the frontend origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---- Response models (the typed contract shown in /docs) ----
class Summary(BaseModel):
    invited: int
    confirmed: int
    declined: int
    no_response: int
    expected_headcount: int


class StatusBreakdown(BaseModel):
    confirmed: int
    declined: int
    pending: int


class GroupRow(BaseModel):
    group: str
    invited: int
    confirmed: int
    expected: int


class RecentUpdate(BaseModel):
    name: str
    group: str
    status: str
    party_size: int
    responded_at: str | None = None


class DashboardResponse(BaseModel):
    summary: Summary
    status_breakdown: StatusBreakdown
    by_group: list[GroupRow]
    recent_updates: list[RecentUpdate]


class ConfirmedGuest(BaseModel):
    name: str
    group: str
    party_size: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard() -> dict:
    """Return the full aggregated dashboard payload."""
    try:
        return get_dashboard_data()
    except Exception as exc:  # surface DB/connection failures as a clear 502
        raise HTTPException(status_code=502, detail=f"Failed to load dashboard data: {exc}")


@app.get("/guests/confirmed", response_model=list[ConfirmedGuest])
def confirmed_guests() -> list:
    """Return confirmed guests (name, group, party_size) for the seating page."""
    try:
        return get_confirmed_guests()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load confirmed guests: {exc}")


@app.get("/auth/google/start")
def google_auth_start(wedding_id: str = "") -> RedirectResponse:
    """Redirects the browser to Google's consent screen. `wedding_id` round-trips
    through the `state` param so imported contacts get tagged to the right wedding."""
    return RedirectResponse(get_auth_url(state=wedding_id))


@app.get("/auth/google/callback")
def google_auth_callback(code: str, state: str = "") -> RedirectResponse:
    """Receives the OAuth code, imports the couple's Google contacts as guests,
    then redirects back to the guestlist page with a result summary in the query string."""
    try:
        contacts = fetch_google_contacts(code)
        guests = contacts_to_guests(contacts)
        if state:
            for guest in guests:
                guest["wedding_id"] = state

        result = import_guests_from_list(guests)
        params = {"imported": result["inserted"], "skipped": len(result["skipped"])}
    except Exception as exc:
        params = {"error": str(exc)}

    return RedirectResponse(f"{FRONTEND_GUESTLIST_URL}?{urlencode(params)}")
