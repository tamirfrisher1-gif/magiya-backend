import pytest
from core.rsvp_logic import validate_phone, summarize_rsvp


def test_valid_israeli_phone():
    assert validate_phone("0501234567") is True
    assert validate_phone("050-123-4567") is True


def test_invalid_phone():
    assert validate_phone("123") is False
    assert validate_phone("abcdefghij") is False
    assert validate_phone("0401234567") is False  # doesn't start with 05


def test_summarize_rsvp_with_dietary():
    guest = {"full_name": "Dana Cohen"}
    result = summarize_rsvp(guest, "confirmed", 2, "vegan")
    assert "Dana Cohen" in result
    assert "confirmed" in result
    assert "vegan" in result


def test_summarize_rsvp_no_dietary():
    guest = {"full_name": "Yossi Levi"}
    result = summarize_rsvp(guest, "confirmed", 1, None)
    assert "Dietary" not in result
