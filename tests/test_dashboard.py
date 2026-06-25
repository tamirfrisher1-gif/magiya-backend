"""
Unit tests for the dashboard aggregation (pure, no DB) and the FastAPI endpoint
(with the data layer monkeypatched, so no DB / network is touched).
"""
from fastapi.testclient import TestClient

from core.dashboard import build_dashboard, UNASSIGNED_GROUP, RECENT_LIMIT
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


# --- API endpoint --------------------------------------------------------

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_dashboard_endpoint(monkeypatch):
    guests, rsvps = _sample()
    canned = build_dashboard(guests, rsvps)
    # patch where the endpoint looks it up (imported into api.main)
    monkeypatch.setattr("api.main.get_dashboard_data", lambda: canned)

    res = client.get("/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {"summary", "status_breakdown", "by_group", "recent_updates"}
    assert body["summary"]["invited"] == 5
    assert body["summary"]["expected_headcount"] == 5
