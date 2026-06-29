"""
Pure dashboard aggregation logic — no database access.

`build_dashboard` takes raw `guests` and `rsvps` rows (lists of dicts, exactly
as returned by Supabase) and computes the aggregated stats the dashboard needs.
Keeping this free of I/O makes it trivial to unit-test without a database.
"""
from typing import Optional

# The only statuses the dashboard recognizes. Anything else (or a missing
# rsvp) is treated as "pending" — i.e. the guest has not responded yet.
_KNOWN_STATUSES = ("confirmed", "declined", "pending")

UNASSIGNED_GROUP = "Unassigned"
RECENT_LIMIT = 10

# Maps the Hebrew dietary labels the bot stores (see bot_handlers/rsvp_flow.py)
# to the keys the dashboard reports. Anything unrecognized/empty counts as "none".
_DIET_LABEL_TO_KEY = {
    "צמחוני": "vegetarian",
    "טבעוני": "vegan",
    "גלאט": "kosher",
    "צליאקי": "celiac",
    "אין": "none",
}
DIET_KEYS = ("vegetarian", "vegan", "kosher", "celiac", "none")


def _normalize_status(rsvp: Optional[dict]) -> str:
    """Map an rsvp row to one of confirmed/declined/pending."""
    if not rsvp:
        return "pending"
    status = rsvp.get("status")
    return status if status in _KNOWN_STATUSES else "pending"


def _party_size(rsvp: Optional[dict]) -> int:
    """Number of people in a confirmed party; defaults to 1 when missing/invalid."""
    try:
        size = int(rsvp.get("party_size")) if rsvp else 1
    except (TypeError, ValueError):
        return 1
    return size if size > 0 else 1


def _group_name(guest: dict) -> str:
    name = (guest.get("group_name") or "").strip()
    return name or UNASSIGNED_GROUP


def _diet_key(label: Optional[str]) -> str:
    """Map a stored Hebrew dietary label to a breakdown key; unknown/empty -> 'none'."""
    if not label:
        return "none"
    return _DIET_LABEL_TO_KEY.get(label.strip(), "none")


def _parse_dietary(rsvp: dict, party_size: int) -> list[str]:
    """Return a per-person list of dietary keys, exactly `party_size` long.

    The bot stores `dietary_restrictions` either as a single label for a party of
    one (or None when 'אין' was chosen) or as multi-line 'אדם N: <label>' for
    larger parties. We pad/truncate to `party_size` so the per-person counts always
    sum to the dashboard's expected headcount.
    """
    raw = (rsvp.get("dietary_restrictions") or "").strip()
    if not raw:
        keys = []
    elif "\n" not in raw and ":" not in raw:
        keys = [_diet_key(raw)]  # single-person value
    else:
        keys = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            label = line.split(":", 1)[1].strip() if ":" in line else line
            keys.append(_diet_key(label))

    if len(keys) < party_size:
        keys += ["none"] * (party_size - len(keys))
    return keys[:party_size]


def build_dashboard(guests: list[dict], rsvps: list[dict]) -> dict:
    """
    Aggregate guests + rsvps into the dashboard contract.

    Returns a dict with `summary`, `status_breakdown`, `by_group` and
    `recent_updates` (see api/README.md for the full shape).
    """
    rsvp_by_guest = {r.get("guest_id"): r for r in rsvps}

    summary = {"invited": len(guests), "confirmed": 0, "declined": 0, "no_response": 0}
    status_breakdown = {"confirmed": 0, "declined": 0, "pending": 0}
    dietary_breakdown = {key: 0 for key in DIET_KEYS}
    expected_headcount = 0
    groups: dict[str, dict] = {}

    for guest in guests:
        rsvp = rsvp_by_guest.get(guest.get("id"))
        status = _normalize_status(rsvp)
        status_breakdown[status] += 1

        group = _group_name(guest)
        grp = groups.setdefault(group, {"group": group, "invited": 0, "confirmed": 0, "expected": 0})
        grp["invited"] += 1

        if status == "confirmed":
            size = _party_size(rsvp)
            summary["confirmed"] += 1
            expected_headcount += size
            grp["confirmed"] += 1
            grp["expected"] += size
            for key in _parse_dietary(rsvp, size):
                dietary_breakdown[key] += 1
        elif status == "declined":
            summary["declined"] += 1
        else:  # pending / no response
            summary["no_response"] += 1

    summary["expected_headcount"] = expected_headcount

    by_group = sorted(groups.values(), key=lambda g: g["group"].lower())

    guest_by_id = {g.get("id"): g for g in guests}
    recent_updates = []
    answered = [r for r in rsvps if r.get("responded_at")]
    answered.sort(key=lambda r: r.get("responded_at"), reverse=True)
    for rsvp in answered[:RECENT_LIMIT]:
        guest = guest_by_id.get(rsvp.get("guest_id"), {})
        status = _normalize_status(rsvp)
        recent_updates.append(
            {
                "name": guest.get("full_name") or "—",
                "group": _group_name(guest),
                "status": status,
                "party_size": _party_size(rsvp) if status == "confirmed" else 0,
                "responded_at": rsvp.get("responded_at"),
            }
        )

    return {
        "summary": summary,
        "status_breakdown": status_breakdown,
        "dietary_breakdown": dietary_breakdown,
        "by_group": by_group,
        "recent_updates": recent_updates,
    }


def build_confirmed_guests(guests: list[dict], rsvps: list[dict]) -> list[dict]:
    """
    Return the list of confirmed guests for the seating page:
    `[{name, group, party_size}]`, one entry per confirmed guest.

    The frontend expands each entry into `party_size` seats so the whole
    party is seated together.
    """
    rsvp_by_guest = {r.get("guest_id"): r for r in rsvps}
    confirmed = []
    for guest in guests:
        rsvp = rsvp_by_guest.get(guest.get("id"))
        if _normalize_status(rsvp) == "confirmed":
            confirmed.append(
                {
                    "name": guest.get("full_name") or "—",
                    "group": _group_name(guest),
                    "party_size": _party_size(rsvp),
                }
            )
    confirmed.sort(key=lambda g: (g["group"].lower(), g["name"].lower()))
    return confirmed
