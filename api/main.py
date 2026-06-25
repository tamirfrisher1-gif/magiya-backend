"""
MAGIYA Dashboard API.

A small FastAPI service that exposes aggregated guest/RSVP statistics as JSON,
so the frontend can build the dashboard UX/UI on top of a stable contract.

Run locally:
    uvicorn api.main:app --reload --port 8001

Interactive schema/docs: http://localhost:8001/docs
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.dashboard import get_dashboard_data

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
