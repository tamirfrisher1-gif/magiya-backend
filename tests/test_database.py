"""
Integration tests — require a real Supabase connection.
Run only when SUPABASE_URL and SUPABASE_KEY are set in your .env.
"""
import pytest
from database.guests import (
    upsert_guest,
    get_guest_by_phone,
    delete_guest,
    import_guests_from_list,
    get_guests_by_group,
    get_all_guest_groups,
    update_guest_group,
    get_guest_stats,
    parse_google_contacts,
    import_from_google_csv,
)

TEST_PHONE = "0500000001"


def test_upsert_and_fetch_guest():
    guest = upsert_guest({"full_name": "Test User", "phone": TEST_PHONE, "group_name": "test"})
    assert guest["phone"] == TEST_PHONE

    fetched = get_guest_by_phone(TEST_PHONE)
    assert fetched is not None
    assert fetched["full_name"] == "Test User"

    delete_guest(fetched["id"])
    assert get_guest_by_phone(TEST_PHONE) is None


# --- parse_google_contacts ---

def test_parse_google_contacts_basic(tmp_path):
    """A standard Google Contacts CSV is correctly parsed into a clean guest list."""
    csv_content = (
        "Name,Phone 1 - Value,Group Membership\n"
        "Dana Cohen,+972-50-123-4567,* myContacts ::: Familie\n"
        "Yossi Levi,0521234567,* myContacts ::: Amis\n"
    )
    csv_file = tmp_path / "contacts.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = parse_google_contacts(str(csv_file))
    assert len(result) == 2
    assert result[0]["full_name"] == "Dana Cohen"
    assert result[0]["phone"] == "0501234567"
    assert result[0]["group_name"] == "Familie"
    assert result[1]["phone"] == "0521234567"
    assert result[1]["group_name"] == "Amis"


def test_parse_google_contacts_skips_no_phone(tmp_path):
    """A contact without a phone number is skipped."""
    csv_content = (
        "Name,Phone 1 - Value,Group Membership\n"
        "No Phone Person,,Familie\n"
        "Valid Person,0501111111,Amis\n"
    )
    csv_file = tmp_path / "contacts.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = parse_google_contacts(str(csv_file))
    assert len(result) == 1
    assert result[0]["full_name"] == "Valid Person"


# --- import_guests_from_list ---

def test_import_basic():
    """Two valid guests are inserted and the summary reports 2 inserted, 0 skipped."""
    guests = [
        {"full_name": "Alice Levi", "phone": "0500000010", "group_name": "family"},
        {"full_name": "Bob Cohen", "phone": "0500000011", "group_name": "friends"},
    ]
    result = import_guests_from_list(guests)
    assert result["inserted"] == 2
    assert len(result["skipped"]) == 0
    for g in guests:
        fetched = get_guest_by_phone(g["phone"])
        if fetched:
            delete_guest(fetched["id"])


def test_import_skips_missing_phone():
    """A row without a phone number is skipped; the valid row is still inserted."""
    guests = [
        {"full_name": "No Phone Person", "group_name": "family"},
        {"full_name": "Valid Person", "phone": "0500000012", "group_name": "friends"},
    ]
    result = import_guests_from_list(guests)
    assert result["inserted"] == 1
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "missing_phone"
    fetched = get_guest_by_phone("0500000012")
    if fetched:
        delete_guest(fetched["id"])


def test_import_skips_invalid_phone():
    """A row with a phone number that doesn't match Israeli format is skipped."""
    guests = [
        {"full_name": "Bad Phone Person", "phone": "123", "group_name": "family"},
        {"full_name": "Valid Person", "phone": "0500000014", "group_name": "family"},
    ]
    result = import_guests_from_list(guests)
    assert result["inserted"] == 1
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "invalid_phone"
    fetched = get_guest_by_phone("0500000014")
    if fetched:
        delete_guest(fetched["id"])


def test_import_handles_duplicates():
    """Importing a guest whose phone already exists updates the record instead of failing."""
    guest = {"full_name": "Dupe Person", "phone": "0500000013", "group_name": "work"}
    import_guests_from_list([guest])
    updated = {**guest, "full_name": "Dupe Person Updated"}
    result = import_guests_from_list([updated])
    assert result["inserted"] == 1
    fetched = get_guest_by_phone("0500000013")
    assert fetched is not None
    assert fetched["full_name"] == "Dupe Person Updated"
    delete_guest(fetched["id"])


# --- get_guests_by_group ---

def test_get_guests_by_group():
    """Only guests from the requested group are returned; others are excluded."""
    upsert_guest({"full_name": "Family Member", "phone": "0500000020", "group_name": "family"})
    upsert_guest({"full_name": "Work Colleague", "phone": "0500000021", "group_name": "work"})

    family_guests = get_guests_by_group("family")
    phones = [g["phone"] for g in family_guests]
    assert "0500000020" in phones
    assert "0500000021" not in phones

    for phone in ["0500000020", "0500000021"]:
        g = get_guest_by_phone(phone)
        if g:
            delete_guest(g["id"])


# --- get_all_guest_groups ---

def test_get_all_guest_groups():
    """Returns all distinct group names present in the guest table."""
    upsert_guest({"full_name": "Person A", "phone": "0500000040", "group_name": "famille"})
    upsert_guest({"full_name": "Person B", "phone": "0500000041", "group_name": "amis"})
    upsert_guest({"full_name": "Person C", "phone": "0500000042", "group_name": "famille"})

    groups = get_all_guest_groups()
    assert "famille" in groups
    assert "amis" in groups
    assert groups == sorted(set(groups))  # sorted and no duplicates

    for phone in ["0500000040", "0500000041", "0500000042"]:
        g = get_guest_by_phone(phone)
        if g:
            delete_guest(g["id"])


# --- update_guest_group ---

def test_update_guest_group():
    """A guest's group is correctly updated."""
    upsert_guest({"full_name": "Move Me", "phone": "0500000050", "group_name": "amis"})

    updated = update_guest_group("0500000050", "famille")
    assert updated is not None
    assert updated["group_name"] == "famille"

    fetched = get_guest_by_phone("0500000050")
    assert fetched["group_name"] == "famille"
    delete_guest(fetched["id"])


def test_update_guest_group_not_found():
    """Returns None if the phone number doesn't exist in the database."""
    result = update_guest_group("0599999999", "famille")
    assert result is None


# --- import_from_google_csv ---

def test_import_from_google_csv(tmp_path):
    """A Google Contacts CSV is parsed and inserted into Supabase in one call."""
    csv_content = (
        "Name,Phone 1 - Value,Group Membership\n"
        "Full Flow Person,0500000060,* myContacts ::: famille\n"
    )
    csv_file = tmp_path / "contacts.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = import_from_google_csv(str(csv_file))
    assert result["inserted"] == 1
    fetched = get_guest_by_phone("0500000060")
    assert fetched is not None
    assert fetched["full_name"] == "Full Flow Person"
    delete_guest(fetched["id"])


# --- get_guest_stats ---

def test_get_guest_stats_counts():
    """Stats reflect the correct total and per-group counts after inserting known test guests."""
    test_guests = [
        {"full_name": "Stats F1", "phone": "0500000030", "group_name": "family"},
        {"full_name": "Stats F2", "phone": "0500000031", "group_name": "family"},
        {"full_name": "Stats Fr1", "phone": "0500000032", "group_name": "friends"},
    ]
    for g in test_guests:
        upsert_guest(g)

    stats = get_guest_stats()
    assert stats["total"] >= 3
    assert stats["by_group"].get("family", 0) >= 2
    assert stats["by_group"].get("friends", 0) >= 1

    for g in test_guests:
        fetched = get_guest_by_phone(g["phone"])
        if fetched:
            delete_guest(fetched["id"])
