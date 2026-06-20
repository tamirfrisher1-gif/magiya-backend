def validate_phone(phone: str) -> bool:
    """Accepts Israeli mobile numbers: 10 digits starting with 05."""
    digits = phone.replace("-", "").replace(" ", "")
    return digits.isdigit() and len(digits) == 10 and digits.startswith("05")


def summarize_rsvp(guest: dict, status: str, party_size: int, dietary: str | None) -> str:
    name = guest.get("full_name", "Guest")
    lines = [f"RSVP Summary for {name}:", f"  Status: {status}", f"  Party size: {party_size}"]
    if dietary:
        lines.append(f"  Dietary: {dietary}")
    return "\n".join(lines)
