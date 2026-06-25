"""
Integration tests for weddings, groups, and seating algorithm.
Requires a real Supabase connection (SUPABASE_URL + SUPABASE_KEY in .env).
All tests clean up after themselves.
"""
import pytest
from database.weddings import create_wedding, get_wedding
from database.groups import create_group, get_groups, delete_group
from database.seating import get_seating_plan, get_seating_by_table, clear_seating
from database.guests import upsert_guest, get_guest_by_phone, delete_guest
from database.client import db
from core.seating_algorithm import assign_seats, run_seating

TEST_WEDDING_ID = "test-wedding-seating-2026"
TEST_CAPACITY = 3  # small capacity so we can test table overflow easily


def _cleanup_wedding():
    """Deletes the test wedding (cascades to guests, groups, seating_assignments)."""
    db.table("seating_assignments").delete().eq("wedding_id", TEST_WEDDING_ID).execute()
    db.table("groups").delete().eq("wedding_id", TEST_WEDDING_ID).execute()
    # Delete guests that belong to this wedding
    guests = db.table("guests").select("id").eq("wedding_id", TEST_WEDDING_ID).execute().data
    for g in guests:
        db.table("guests").delete().eq("id", g["id"]).execute()
    db.table("weddings").delete().eq("id", TEST_WEDDING_ID).execute()


def _insert_test_guests(guests: list[dict]):
    """Inserts guests with the test wedding_id."""
    for g in guests:
        upsert_guest({**g, "wedding_id": TEST_WEDDING_ID})


# ── Weddings ────────────────────────────────────────────────────────────────

def test_create_and_get_wedding():
    """A wedding can be created and retrieved by its id."""
    _cleanup_wedding()
    w = create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)
    assert w["id"] == TEST_WEDDING_ID
    assert w["bride_name"] == "Sarah"
    assert w["table_capacity"] == TEST_CAPACITY

    fetched = get_wedding(TEST_WEDDING_ID)
    assert fetched is not None
    assert fetched["groom_name"] == "David"

    _cleanup_wedding()


def test_get_wedding_not_found():
    """Returns None for a wedding id that does not exist."""
    result = get_wedding("non-existent-wedding-id-xyz")
    assert result is None


def test_create_wedding_upsert():
    """Creating the same wedding twice updates it instead of failing."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", 10)
    updated = create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", 12)
    assert updated["table_capacity"] == 12
    _cleanup_wedding()


# ── Groups ───────────────────────────────────────────────────────────────────

def test_create_and_get_groups():
    """Groups created for a wedding are returned by get_groups, sorted alphabetically."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    create_group(TEST_WEDDING_ID, "Famille côté marié")
    create_group(TEST_WEDDING_ID, "Amis communs")
    create_group(TEST_WEDDING_ID, "Collègues")

    groups = get_groups(TEST_WEDDING_ID)
    assert "Amis communs" in groups
    assert "Famille côté marié" in groups
    assert "Collègues" in groups
    assert groups == sorted(groups)

    _cleanup_wedding()


def test_create_group_duplicate_is_ignored():
    """Creating the same group name twice does not raise an error."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    create_group(TEST_WEDDING_ID, "Famille")
    create_group(TEST_WEDDING_ID, "Famille")  # should not crash

    groups = get_groups(TEST_WEDDING_ID)
    assert groups.count("Famille") == 1

    _cleanup_wedding()


def test_delete_group():
    """A group can be deleted; it no longer appears in get_groups."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    create_group(TEST_WEDDING_ID, "Famille")
    create_group(TEST_WEDDING_ID, "Amis")
    delete_group(TEST_WEDDING_ID, "Famille")

    groups = get_groups(TEST_WEDDING_ID)
    assert "Famille" not in groups
    assert "Amis" in groups

    _cleanup_wedding()


# ── Seating algorithm ────────────────────────────────────────────────────────

def test_assign_seats_keeps_group_together():
    """All guests from the same group that fit in one table are assigned to the same table."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    _insert_test_guests([
        {"full_name": "Alice", "phone": "0500000091", "group_name": "famille"},
        {"full_name": "Bob",   "phone": "0500000092", "group_name": "famille"},
        {"full_name": "Carol", "phone": "0500000093", "group_name": "famille"},
    ])

    assignments = assign_seats(TEST_WEDDING_ID, TEST_CAPACITY)
    tables = {a["guest_phone"]: a["table_number"] for a in assignments}

    # All three family guests fit in one table (capacity = 3)
    assert tables["0500000091"] == tables["0500000092"] == tables["0500000093"]

    _cleanup_wedding()


def test_assign_seats_overflow_to_next_table():
    """A group larger than table capacity spills into the next table."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    # 4 guests in one group, capacity = 3 → must use 2 tables
    _insert_test_guests([
        {"full_name": "F1", "phone": "0500000091", "group_name": "famille"},
        {"full_name": "F2", "phone": "0500000092", "group_name": "famille"},
        {"full_name": "F3", "phone": "0500000093", "group_name": "famille"},
        {"full_name": "F4", "phone": "0500000094", "group_name": "famille"},
    ])

    assignments = assign_seats(TEST_WEDDING_ID, TEST_CAPACITY)
    tables_used = {a["table_number"] for a in assignments}
    assert len(tables_used) == 2

    _cleanup_wedding()


def test_assign_seats_different_groups_on_different_tables():
    """Two groups that together exceed capacity are placed on separate tables."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    # famille: 3 guests (fills table 1), amis: 2 guests (go to table 2 or 3)
    _insert_test_guests([
        {"full_name": "F1", "phone": "0500000091", "group_name": "famille"},
        {"full_name": "F2", "phone": "0500000092", "group_name": "famille"},
        {"full_name": "F3", "phone": "0500000093", "group_name": "famille"},
        {"full_name": "A1", "phone": "0500000094", "group_name": "amis"},
        {"full_name": "A2", "phone": "0500000095", "group_name": "amis"},
    ])

    assignments = assign_seats(TEST_WEDDING_ID, TEST_CAPACITY)
    by_phone = {a["guest_phone"]: a["table_number"] for a in assignments}

    famille_tables = {by_phone[p] for p in ["0500000091", "0500000092", "0500000093"]}
    amis_tables    = {by_phone[p] for p in ["0500000094", "0500000095"]}

    # famille fills exactly one table; amis must start on a different table
    assert len(famille_tables) == 1
    assert famille_tables.isdisjoint(amis_tables)

    _cleanup_wedding()


def test_run_seating_saves_to_supabase():
    """run_seating() saves assignments to seating_assignments and returns the right summary."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    _insert_test_guests([
        {"full_name": "G1", "phone": "0500000091", "group_name": "famille"},
        {"full_name": "G2", "phone": "0500000092", "group_name": "famille"},
        {"full_name": "G3", "phone": "0500000093", "group_name": "amis"},
    ])

    result = run_seating(TEST_WEDDING_ID)

    assert result["total"] == 3
    assert result["tables_used"] >= 1

    # Verify rows are actually in Supabase
    saved = get_seating_plan(TEST_WEDDING_ID)
    assert len(saved) == 3

    _cleanup_wedding()


def test_run_seating_invalid_wedding():
    """run_seating raises ValueError for a wedding that doesn't exist."""
    with pytest.raises(ValueError):
        run_seating("this-wedding-does-not-exist")


def test_clear_seating():
    """clear_seating() removes all assignments for a wedding."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    _insert_test_guests([
        {"full_name": "G1", "phone": "0500000091", "group_name": "famille"},
    ])

    run_seating(TEST_WEDDING_ID)
    assert len(get_seating_plan(TEST_WEDDING_ID)) == 1

    clear_seating(TEST_WEDDING_ID)
    assert len(get_seating_plan(TEST_WEDDING_ID)) == 0

    _cleanup_wedding()


def test_get_seating_by_table():
    """get_seating_by_table returns a dict mapping each table number to its guest phones."""
    _cleanup_wedding()
    create_wedding(TEST_WEDDING_ID, "Sarah", "David", "2026-08-15", TEST_CAPACITY)

    _insert_test_guests([
        {"full_name": "G1", "phone": "0500000091", "group_name": "famille"},
        {"full_name": "G2", "phone": "0500000092", "group_name": "famille"},
        {"full_name": "G3", "phone": "0500000093", "group_name": "famille"},
        {"full_name": "G4", "phone": "0500000094", "group_name": "amis"},
    ])

    run_seating(TEST_WEDDING_ID)
    by_table = get_seating_by_table(TEST_WEDDING_ID)

    # Should have at least 2 tables; every guest appears exactly once
    all_phones = [p for phones in by_table.values() for p in phones]
    assert len(all_phones) == 4
    assert len(by_table) >= 2

    _cleanup_wedding()
