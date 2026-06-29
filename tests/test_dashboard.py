"""
Unit tests for the dashboard aggregation (pure, no DB) and the FastAPI endpoint
(with the data layer monkeypatched, so no DB / network is touched).
"""
from fastapi.testclient import TestClient

from core.dashboard import (
    build_dashboard,
    build_confirmed_guests,
    _parse_dietary,
    UNASSIGNED_GROUP,
    RECENT_LIMIT,
    DIET_KEYS,
)
from api.main import app

client = TestClient(app)


# --- sample data ---------------------------------------------------------

def _sample():
    guests = [
        {"id": "g1", "full_name": "Alice", "group_name": "family"},
        {"id": "g2", "full_name": "Bob", "group_name": "family"},
        {"id": "g3", "full_name": "Carol", "group_name": "friends"},
        {"id": "g4", "full_name": "Dan", "group_name": "friends"},
        {"id": "g5", "full_name": "Eve", "group_name": ""},  # no group
    ]
    rsvps = [
        {"guest_id": "g1", "status": "confirmed", "party_size": 2, "responded_at": "2026-06-20T10:00:00Z"},
        {"guest_id": "g2", "status": "declined", "party_size": 1, "responded_at": "2026-06-21T10:00:00Z"},
        {"guest_id": "g3", "status": "confirmed", "party_size": 3, "responded_at": "2026-06-22T10:00:00Z"},
        {"guest_id": "g4", "status": "pending", "responded_at": "2026-06-23T10:00:00Z"},
        # g5 has no rsvp at all -> counts as no_response
    ]
    return guests, rsvps


# --- build_dashboard -----------------------------------------------------

def test_summary_counts():
    dash = build_dashboard(*_sample())
    s = dash["summary"]
    assert s["invited"] == 5
    assert s["confirmed"] == 2
    assert s["declined"] == 1
    assert s["no_response"] == 2  # g4 pending + g5 missing
    assert s["expected_headcount"] == 5  # 2 + 3


def test_status_breakdown():
    dash = build_dashboard(*_sample())
    assert dash["status_breakdown"] == {"confirmed": 2, "declined": 1, "pending": 2}


def test_by_group_aggregation():
    dash = build_dashboard(*_sample())
    by_group = {g["group"]: g for g in dash["by_group"]}
    assert by_group["family"] == {"group": "family", "invited": 2, "confirmed": 1, "expected": 2}
    assert by_group["friends"] == {"group": "friends", "invited": 2, "confirmed": 1, "expected": 3}
    assert by_group[UNASSIGNED_GROUP]["invited"] == 1
    # groups are sorted alphabetically (case-insensitive)
    names = [g["group"] for g in dash["by_group"]]
    assert names == sorted(names, key=str.lower)


def test_recent_updates_order_and_shape():
    dash = build_dashboard(*_sample())
    recent = dash["recent_updates"]
    assert len(recent) == 4  # only rsvps with responded_at
    # newest first
    assert recent[0]["name"] == "Dan"
    assert recent[-1]["name"] == "Alice"
    # confirmed carries party_size; non-confirmed is 0
    alice = next(r for r in recent if r["name"] == "Alice")
    assert alice["party_size"] == 2
    dan = next(r for r in recent if r["name"] == "Dan")
    assert dan["status"] == "pending"
    assert dan["party_size"] == 0


def test_recent_updates_capped():
    guests = [{"id": f"g{i}", "full_name": f"G{i}", "group_name": "x"} for i in range(20)]
    rsvps = [
        {"guest_id": f"g{i}", "status": "confirmed", "party_size": 1,
         "responded_at": f"2026-06-{i + 1:02d}T10:00:00Z"}
        for i in range(20)
    ]
    dash = build_dashboard(guests, rsvps)
    assert len(dash["recent_updates"]) == RECENT_LIMIT


def test_empty_input():
    dash = build_dashboard([], [])
    assert dash["summary"] == {
        "invited": 0, "confirmed": 0, "declined": 0,
        "no_response": 0, "expected_headcount": 0,
    }
    assert dash["by_group"] == []
    assert dash["recent_updates"] == []


def test_unknown_status_is_pending():
    guests = [{"id": "g1", "full_name": "X", "group_name": "g"}]
    rsvps = [{"guest_id": "g1", "status": "weird"}]
    dash = build_dashboard(guests, rsvps)
    assert dash["status_breakdown"]["pending"] == 1
    assert dash["summary"]["no_response"] == 1


# --- dietary breakdown ---------------------------------------------------

def test_parse_dietary_single_person():
    assert _parse_dietary({"dietary_restrictions": "צמחוני"}, 1) == ["vegetarian"]
    assert _parse_dietary({"dietary_restrictions": "טבעוני"}, 1) == ["vegan"]
    assert _parse_dietary({"dietary_restrictions": "גלאט"}, 1) == ["kosher"]
    assert _parse_dietary({"dietary_restrictions": "צליאקי"}, 1) == ["celiac"]


def test_parse_dietary_none_when_missing():
    # the bot stores None when 'אין' was chosen for a party of one
    assert _parse_dietary({"dietary_restrictions": None}, 1) == ["none"]
    assert _parse_dietary({}, 1) == ["none"]


def test_parse_dietary_multi_person():
    raw = "אדם 1: צמחוני\nאדם 2: אין\nאדם 3: טבעוני"
    assert _parse_dietary({"dietary_restrictions": raw}, 3) == ["vegetarian", "none", "vegan"]


def test_parse_dietary_pads_and_truncates_to_party_size():
    # fewer recorded lines than the party size -> remainder counts as 'none'
    assert _parse_dietary({"dietary_restrictions": "אדם 1: גלאט"}, 3) == ["kosher", "none", "none"]
    # more lines than party size -> truncated
    raw = "אדם 1: צמחוני\nאדם 2: טבעוני"
    assert _parse_dietary({"dietary_restrictions": raw}, 1) == ["vegetarian"]


def test_parse_dietary_unknown_label_is_none():
    assert _parse_dietary({"dietary_restrictions": "פיצה"}, 1) == ["none"]


def test_dietary_breakdown_sums_to_expected_headcount():
    guests = [
        {"id": "g1", "full_name": "A", "group_name": "x"},
        {"id": "g2", "full_name": "B", "group_name": "x"},
        {"id": "g3", "full_name": "C", "group_name": "x"},
    ]
    rsvps = [
        {"guest_id": "g1", "status": "confirmed", "party_size": 1, "dietary_restrictions": "צמחוני"},
        {"guest_id": "g2", "status": "confirmed", "party_size": 2,
         "dietary_restrictions": "אדם 1: גלאט\nאדם 2: טבעוני"},
        {"guest_id": "g3", "status": "declined", "party_size": 1, "dietary_restrictions": "צליאקי"},
    ]
    dash = build_dashboard(guests, rsvps)
    db = dash["dietary_breakdown"]
    assert db == {"vegetarian": 1, "vegan": 1, "kosher": 1, "celiac": 0, "none": 0}
    # declined guests are excluded; per-person counts match expected headcount
    assert sum(db.values()) == dash["summary"]["expected_headcount"] == 3


def test_dietary_breakdown_keys_always_present():
    dash = build_dashboard([], [])
    assert set(dash["dietary_breakdown"].keys()) == set(DIET_KEYS)
    assert all(v == 0 for v in dash["dietary_breakdown"].values())


# --- build_confirmed_guests ----------------------------------------------

def test_confirmed_guests_only_confirmed():
    confirmed = build_confirmed_guests(*_sample())
    # only g1 (Alice) and g3 (Carol) are confirmed
    names = [g["name"] for g in confirmed]
    assert names == ["Alice", "Carol"]  # sorted by (group, name): family, friends
    alice = next(g for g in confirmed if g["name"] == "Alice")
    assert alice == {"name": "Alice", "group": "family", "party_size": 2}


def test_confirmed_guests_empty():
    assert build_confirmed_guests([], []) == []


# --- API endpoint --------------------------------------------------------

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_dashboard_endpoint(monkeypatch):
    guests, rsvps = _sample()
    canned = build_dashboard(guests, rsvps)
    # patch where the endpoint looks it up (imported into api.main); the endpoint
    # passes a wedding_id arg, so the stub must accept it.
    monkeypatch.setattr("api.main.get_dashboard_data", lambda *args, **kwargs: canned)

    res = client.get("/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "summary", "status_breakdown", "dietary_breakdown", "by_group", "recent_updates",
    }
    assert body["summary"]["invited"] == 5
    assert body["summary"]["expected_headcount"] == 5
