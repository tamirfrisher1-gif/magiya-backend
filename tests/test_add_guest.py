"""
Unit tests for manually adding a guest:
- the pure-ish data helper `add_manual_guest` (phone normalization + validation),
  with the Supabase upsert monkeypatched so no DB/network is touched;
- the POST /guests endpoint (success, invalid phone -> 400, duplicate -> 409).
"""
import pytest
from fastapi.testclient import TestClient

import database.guests as guests
from api.main import app

client = TestClient(app)

VALID = {"wedding_id": "w1", "full_name": "Maya Cohen", "phone": "052-000-0000", "group_name": "Friends"}


# --- add_manual_guest (data helper) -------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("052-000-0000", "0520000000"),
    ("0520000000", "0520000000"),
    ("+972 52 000 0000", "0520000000"),
    ("972-52-000-0000", "0520000000"),
])
def test_add_manual_guest_normalizes_phone(monkeypatch, raw, expected):
    captured = {}
    monkeypatch.setattr(guests, "upsert_guest", lambda data: {**data, "id": "g-123"})
    out = guests.add_manual_guest("w1", "Maya", raw, "Friends")
    assert out["phone"] == expected
    assert out["wedding_id"] == "w1"
    assert out["invited"] is True
    assert out["id"] == "g-123"


@pytest.mark.parametrize("bad", ["", "12345", "03-000-0000", "abcdefghij"])
def test_add_manual_guest_rejects_bad_phone(monkeypatch, bad):
    monkeypatch.setattr(guests, "upsert_guest", lambda data: {**data, "id": "x"})
    with pytest.raises(ValueError):
        guests.add_manual_guest("w1", "Maya", bad, "Friends")


def test_add_manual_guest_requires_fields(monkeypatch):
    monkeypatch.setattr(guests, "upsert_guest", lambda data: {**data, "id": "x"})
    with pytest.raises(ValueError):
        guests.add_manual_guest("w1", "  ", "0520000000", "Friends")
    with pytest.raises(ValueError):
        guests.add_manual_guest("w1", "Maya", "0520000000", "  ")


# --- POST /guests endpoint ----------------------------------------------

def test_post_guest_success(monkeypatch):
    monkeypatch.setattr("api.main.get_guest_in_wedding", lambda wid, phone: None)
    monkeypatch.setattr("api.main.add_manual_guest",
                        lambda **kw: {"id": "g-9", "full_name": kw["full_name"],
                                      "phone": "0520000000", "group_name": kw["group_name"],
                                      "wedding_id": kw["wedding_id"], "invited": True})
    monkeypatch.setattr("api.main.BOT_USERNAME", "magiya_bot")
    res = client.post("/guests", json=VALID)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "g-9"
    assert body["invite_link"] == "https://t.me/magiya_bot?start=g-9"


def test_post_guest_invalid_phone(monkeypatch):
    monkeypatch.setattr("api.main.get_guest_in_wedding", lambda wid, phone: None)
    res = client.post("/guests", json={**VALID, "phone": "123"})
    assert res.status_code == 400


def test_post_guest_duplicate_returns_409_without_overwrite(monkeypatch):
    existing = {"id": "g-existing", "full_name": "Maya Cohen", "phone": "0520000000",
                "group_name": "Friends", "wedding_id": "w1"}
    monkeypatch.setattr("api.main.get_guest_in_wedding", lambda wid, phone: existing)
    monkeypatch.setattr("api.main.BOT_USERNAME", "magiya_bot")

    called = {"added": False}
    def _should_not_run(**kw):
        called["added"] = True
        return {}
    monkeypatch.setattr("api.main.add_manual_guest", _should_not_run)

    res = client.post("/guests", json=VALID)
    assert res.status_code == 409
    assert called["added"] is False  # never overwrote / created
    detail = res.json()["detail"]
    assert "already" in detail["message"].lower()
    assert detail["guest"]["invite_link"] == "https://t.me/magiya_bot?start=g-existing"
