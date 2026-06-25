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


def build_dashboard(guests: list[dict], rsvps: list[dict]) -> dict:
    """
    Aggregate guests + rsvps into the dashboard contract.

    Returns a dict with `summary`, `status_breakdown`, `by_group` and
    `recent_updates` (see api/README.md for the full shape).
    """
    rsvp_by_guest = {r.get("guest_id"): r for r in rsvps}

    summary = {"invited": len(guests), "confirmed": 0, "declined": 0, "no_response": 0}
    status_breakdown = {"confirmed": 0, "declined": 0, "pending": 0}
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
        "by_group": by_group,
        "recent_updates": recent_updates,
    }
