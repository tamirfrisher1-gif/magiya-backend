"""
MAGIYA Dashboard API + Telegram Bot (webhook mode).

Run locally:
    uvicorn api.main:app --reload --port 8001
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from database.dashboard import get_dashboard_data, get_confirmed_guests
from database.guests import (
    import_guests_from_list,
    get_invited_guests_for_wedding,
    get_guest_in_wedding,
    add_manual_guest,
    get_wedding_groups,
)
from core.google_contacts import get_auth_url, fetch_google_contacts, contacts_to_guests
from core.invitation_generator import generate_invitation_image_b64
from config.settings import FRONTEND_GUESTLIST_URL, BOT_USERNAME, TELEGRAM_BOT_TOKEN
from bot_handlers.commands import ping, help_command
from bot_handlers.rsvp_flow import rsvp_conversation
from bot_handlers.admin import stats, seating

logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://magiya-api.onrender.com/webhook"
HEALTH_URL = "https://magiya-api.onrender.com/health"

_bot = None  # telegram Application instance


async def _keep_alive():
    """Ping our own /health every 60 s so Render never spins down."""
    await asyncio.sleep(30)  # let startup finish first
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(HEALTH_URL, timeout=10)
            except Exception:
                pass
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot
    _bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    _bot.add_handler(CommandHandler("ping", ping))
    _bot.add_handler(CommandHandler("help", help_command))
    _bot.add_handler(CommandHandler("stats", stats))
    _bot.add_handler(CommandHandler("seating", seating))
    _bot.add_handler(rsvp_conversation)
    await _bot.initialize()
    await _bot.start()
    await _bot.bot.set_webhook(WEBHOOK_URL)
    logger.info("Telegram webhook registered at %s", WEBHOOK_URL)
    keep_alive_task = asyncio.create_task(_keep_alive())
    yield
    keep_alive_task.cancel()
    await _bot.stop()
    await _bot.shutdown()


app = FastAPI(
    title="MAGIYA Dashboard API",
    version="1.0",
    description="Aggregated guest & RSVP statistics for the MAGIYA wedding dashboard.",
    lifespan=lifespan,
)

# Open CORS for the course project. Lock this down to the frontend origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
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


class DietaryBreakdown(BaseModel):
    vegetarian: int
    vegan: int
    kosher: int
    celiac: int
    none: int


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
    dietary_breakdown: DietaryBreakdown
    by_group: list[GroupRow]
    recent_updates: list[RecentUpdate]


class ConfirmedGuest(BaseModel):
    name: str
    group: str
    party_size: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Telegram calls this endpoint for every user message."""
    data = await request.json()
    update = Update.de_json(data, _bot.bot)
    await _bot.process_update(update)
    return {"ok": True}


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard(wedding_id: str | None = None) -> dict:
    """Return aggregated dashboard payload, filtered to a specific wedding when wedding_id is given."""
    try:
        return get_dashboard_data(wedding_id)
    except Exception as exc:  # surface DB/connection failures as a clear 502
        raise HTTPException(status_code=502, detail=f"Failed to load dashboard data: {exc}")


@app.get("/guests/invited")
def invited_guests_with_links(wedding_id: str) -> list:
    """Return invited guests for a wedding with their personal Telegram invite links."""
    try:
        guests = get_invited_guests_for_wedding(wedding_id)
        for g in guests:
            g["invite_link"] = f"https://t.me/{BOT_USERNAME}?start={g['id']}" if BOT_USERNAME else ""
        return guests
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load invited guests: {exc}")


class NewGuest(BaseModel):
    wedding_id: str
    full_name: str
    phone: str
    group_name: str


def _invite_link(guest_id: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={guest_id}" if BOT_USERNAME else ""


@app.get("/groups")
def wedding_groups(wedding_id: str) -> list[str]:
    """All group names defined for a wedding (for the manual-add dropdown)."""
    try:
        return get_wedding_groups(wedding_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load groups: {exc}")


@app.post("/guests")
def add_guest(body: NewGuest) -> dict:
    """Manually add a single guest (not from Google import) and return their record
    with a freshly-generated personal Telegram invite link.

    If the phone is already in this wedding we refuse to overwrite and return 409 with
    the existing guest's link, so a genuine new add always mints a brand-new link."""
    try:
        existing = get_guest_in_wedding(body.wedding_id, body.phone)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"{existing.get('full_name') or 'This guest'} is already in your list.",
                    "guest": {**existing, "invite_link": _invite_link(existing["id"])},
                },
            )
        guest = add_manual_guest(
            wedding_id=body.wedding_id,
            full_name=body.full_name,
            phone=body.phone,
            group_name=body.group_name,
        )
        return {**guest, "invite_link": _invite_link(guest["id"])}
    except ValueError as exc:  # invalid / missing input
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:  # DB/connection failure
        raise HTTPException(status_code=502, detail=f"Failed to add guest: {exc}")


@app.get("/guests/confirmed", response_model=list[ConfirmedGuest])
def confirmed_guests(wedding_id: str | None = None) -> list:
    """Return confirmed guests (name, group, party_size) for the seating page."""
    try:
        return get_confirmed_guests(wedding_id)
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


class ImageGenRequest(BaseModel):
    description: str = ""
    bride_name: str = ""
    groom_name: str = ""
    wedding_date: str = ""
    style: str = "elegant"
    colors: str = "white and gold"
    elements: str = ""


@app.post("/invitations/generate-image")
async def generate_image(body: ImageGenRequest) -> dict:
    """Generate a wedding invitation image via gpt-image-1; returns a base64 data URL."""
    try:
        data_url = generate_invitation_image_b64(
            description=body.description,
            bride_name=body.bride_name,
            groom_name=body.groom_name,
            wedding_date=body.wedding_date,
            style=body.style,
            colors=body.colors,
            elements=body.elements,
        )
        return {"image": data_url}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}")
