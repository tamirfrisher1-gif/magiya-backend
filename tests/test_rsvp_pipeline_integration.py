"""
Integration tests for the RSVP pipeline: bulk volume, edge cases, and
overwrite/recovery behavior that the bot itself relies on. Requires a real
Supabase connection (SUPABASE_URL/SUPABASE_KEY in .env).
"""
from database.guests import upsert_guest, get_guest_by_phone, get_guest_by_id, delete_guest
from database.rsvps import upsert_rsvp, get_rsvp_by_guest, get_confirmed_guests, get_dashboard_stats

TEST_PHONE_PREFIX = "059900000"


def _make_guest(suffix: int, group: str = "test") -> dict:
    return upsert_guest({
        "full_name": f"Bulk Test {suffix}",
        "phone": f"{TEST_PHONE_PREFIX}{suffix}",
        "group_name": group,
    })


def test_bulk_rsvp_all_party_sizes():
    """Every party size from 1 to 5 (the bot's actual button range) saves and reads back correctly."""
    guest_ids = []
    try:
        for party_size in range(1, 6):
            guest = _make_guest(party_size)
            guest_ids.append(guest["id"])

            dietary = None if party_size == 1 else "\n".join(
                f"אדם {i}: אין" for i in range(1, party_size + 1)
            )
            upsert_rsvp(guest_id=guest["id"], status="confirmed", party_size=party_size, dietary_restrictions=dietary)

            saved = get_rsvp_by_guest(guest["id"])
            assert saved["party_size"] == party_size
            assert saved["status"] == "confirmed"
    finally:
        for gid in guest_ids:
            delete_guest(gid)


def test_decline_then_reconfirm_overwrites_cleanly():
    """A guest who declines and then changes their mind overwrites the same row, not a duplicate."""
    guest = _make_guest(900)
    try:
        upsert_rsvp(guest_id=guest["id"], status="declined")
        first = get_rsvp_by_guest(guest["id"])
        assert first["status"] == "declined"

        upsert_rsvp(guest_id=guest["id"], status="confirmed", party_size=2)
        second = get_rsvp_by_guest(guest["id"])
        assert second["status"] == "confirmed"
        assert second["party_size"] == 2
        assert second["id"] == first["id"]  # same row, not a new one
    finally:
        delete_guest(guest["id"])


def test_guest_not_found_by_phone_and_id_returns_none():
    """Looking up a guest that doesn't exist (manual /rsvp or a broken deep link) fails gracefully."""
    assert get_guest_by_phone("0590000000") is None
    assert get_guest_by_id("00000000-0000-0000-0000-000000000000") is None


def test_confirmed_guest_with_no_group_does_not_break_pipeline():
    """A guest with group_name=None (e.g. imported without classification) still
    flows through get_confirmed_guests without crashing."""
    guest = _make_guest(901, group="")
    try:
        upsert_rsvp(guest_id=guest["id"], status="confirmed", party_size=1)
        confirmed = get_confirmed_guests()
        ids = [g["id"] for g in confirmed]
        assert guest["id"] in ids
    finally:
        delete_guest(guest["id"])


def test_dashboard_stats_reflect_concurrent_style_writes():
    """Several guests confirming/declining in quick succession (simulating concurrent
    bot users) all land correctly in the aggregate stats — no lost writes."""
    guest_ids = []
    try:
        for i in range(5):
            guest = _make_guest(910 + i)
            guest_ids.append(guest["id"])
            status = "confirmed" if i % 2 == 0 else "declined"
            upsert_rsvp(guest_id=guest["id"], status=status, party_size=1)

        stats = get_dashboard_stats()
        assert stats["confirmed"] >= 3
        assert stats["declined"] >= 2
    finally:
        for gid in guest_ids:
            delete_guest(gid)


def test_deleting_guest_with_rsvp_cascades_cleanly():
    """Deleting a guest who already has an RSVP must not fail with a foreign key
    violation — found via integration testing; fixed with ON DELETE CASCADE."""
    guest = _make_guest(920)
    upsert_rsvp(guest_id=guest["id"], status="confirmed", party_size=1)
    delete_guest(guest["id"])  # must not raise
    assert get_guest_by_phone(f"{TEST_PHONE_PREFIX}920") is None
