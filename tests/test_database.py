"""
Integration tests — require a real Supabase connection.
Run only when SUPABASE_URL and SUPABASE_KEY are set in your .env.
"""
import pytest
from database.guests import upsert_guest, get_guest_by_phone, delete_guest

TEST_PHONE = "0500000001"


def test_upsert_and_fetch_guest():
    guest = upsert_guest({"full_name": "Test User", "phone": TEST_PHONE, "group_name": "test"})
    assert guest["phone"] == TEST_PHONE

    fetched = get_guest_by_phone(TEST_PHONE)
    assert fetched is not None
    assert fetched["full_name"] == "Test User"

    delete_guest(fetched["id"])
    assert get_guest_by_phone(TEST_PHONE) is None
