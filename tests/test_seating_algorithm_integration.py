"""
Integration test for the team's seating algorithm (core/seating_algorithm.py).
Creates a throwaway wedding + guests, runs the real algorithm against them,
and cleans up afterward — never touches real guest/wedding data.
"""
from database.client import db
from database.weddings import create_wedding
from database.guests import upsert_guest
from core.seating_algorithm import run_seating

TEST_WEDDING_ID = "test-seating-wedding-do-not-use"


def _cleanup():
    # Deleting the wedding cascades to guests (wedding_id FK) and
    # seating_assignments (wedding_id FK) per migration 001/003.
    db.table("weddings").delete().eq("id", TEST_WEDDING_ID).execute()


def test_run_seating_assigns_groups_to_tables():
    _cleanup()  # safety net in case a previous failed run left data behind

    create_wedding(
        wedding_id=TEST_WEDDING_ID,
        bride_name="Test Bride",
        groom_name="Test Groom",
        wedding_date="2099-01-01",
        table_capacity=2,
    )

    guests = [
        {"full_name": "Family A", "phone": "0596000001", "group_name": "family", "wedding_id": TEST_WEDDING_ID},
        {"full_name": "Family B", "phone": "0596000002", "group_name": "family", "wedding_id": TEST_WEDDING_ID},
        {"full_name": "Friend A", "phone": "0596000003", "group_name": "friends", "wedding_id": TEST_WEDDING_ID},
        {"full_name": "Friend B", "phone": "0596000004", "group_name": "friends", "wedding_id": TEST_WEDDING_ID},
    ]
    for g in guests:
        upsert_guest(g)

    try:
        result = run_seating(TEST_WEDDING_ID)

        assert result["total"] == 4
        assert result["tables_used"] >= 2  # table_capacity=2, so 4 guests need >= 2 tables

        saved = (
            db.table("seating_assignments")
            .select("guest_phone, table_number")
            .eq("wedding_id", TEST_WEDDING_ID)
            .execute()
            .data
        )
        assert len(saved) == 4

        # Same group should share a table (group_name "family"/"friends" with capacity 2)
        by_table: dict[int, list[str]] = {}
        for row in saved:
            by_table.setdefault(row["table_number"], []).append(row["guest_phone"])
        tables_with_2 = [t for t in by_table.values() if len(t) == 2]
        assert len(tables_with_2) == 2  # family pair + friends pair, each filling one table
    finally:
        _cleanup()


def test_run_seating_unknown_wedding_raises():
    import pytest
    with pytest.raises(ValueError):
        run_seating("this-wedding-id-does-not-exist")
