import csv
from typing import Optional
from database.client import db
from core.rsvp_logic import validate_phone


def get_all_guests() -> list[dict]:
    response = db.table("guests").select("*").execute()
    return response.data


def get_guest_by_phone(phone: str) -> Optional[dict]:
    response = db.table("guests").select("*").eq("phone", phone).maybe_single().execute()
    return response.data if response is not None else None


def upsert_guest(data: dict) -> dict:
    """Insert or update a guest. `data` must include `phone` as the unique key."""
    response = db.table("guests").upsert(data, on_conflict="phone").execute()
    return response.data[0]


def delete_guest(guest_id: str) -> None:
    db.table("guests").delete().eq("id", guest_id).execute()


def import_guests_from_list(guests: list[dict]) -> dict:
    """Bulk-insert/update guests from an Excel or CSV import; returns a summary of inserted and skipped rows."""
    inserted = 0
    skipped: list[dict] = []

    for row in guests:
        phone = str(row.get("phone", "")).strip()

        if not phone:
            skipped.append({"reason": "missing_phone", "row": row})
            continue

        if not validate_phone(phone):
            skipped.append({"reason": "invalid_phone", "row": row})
            continue

        # Strip whitespace from string fields; drop keys with empty or None values
        clean: dict = {
            k: v.strip() if isinstance(v, str) else v
            for k, v in row.items()
            if v is not None and str(v).strip() != ""
        }
        clean["phone"] = phone

        db.table("guests").upsert(clean, on_conflict="phone").execute()
        inserted += 1

    return {"inserted": inserted, "skipped": skipped}


def get_guests_by_group(group_name: str) -> list[dict]:
    """Returns all guests belonging to the given group (e.g. 'family', 'friends', 'work')."""
    response = db.table("guests").select("*").eq("group_name", group_name).execute()
    return response.data


def get_all_guest_groups() -> list[str]:
    """Returns the list of all distinct group names currently used in the guest table."""
    rows = db.table("guests").select("group_name").execute().data
    seen = set()
    groups = []
    for row in rows:
        name = row.get("group_name")
        if name and name not in seen:
            seen.add(name)
            groups.append(name)
    return sorted(groups)


def update_guest_group(phone: str, new_group: str) -> Optional[dict]:
    """Updates the group of a guest identified by phone number. Returns the updated guest or None if not found."""
    guest = get_guest_by_phone(phone)
    if not guest:
        return None
    response = (
        db.table("guests")
        .update({"group_name": new_group})
        .eq("phone", phone)
        .execute()
    )
    return response.data[0] if response.data else None


def _clean_phone(raw: str) -> str:
    """Normalizes a phone number to Israeli format (e.g. +972-50-123-4567 → 0501234567)."""
    digits = raw.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    return digits


def parse_google_contacts(file_path: str) -> list[dict]:
    """Parses a Google Contacts CSV export and returns a list ready for import_guests_from_list."""
    guests: list[dict] = []
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            raw_phone = row.get("Phone 1 - Value", "").strip()
            raw_group = row.get("Group Membership", "").strip()

            if not raw_phone:
                continue

            # Google exports groups as "* myContacts ::: Friends" — keep only the label
            group_label = raw_group.split(":::")[-1].strip() if ":::" in raw_group else raw_group
            group = group_label or None

            guests.append({
                "full_name": name or "Unknown",
                "phone": _clean_phone(raw_phone),
                "group_name": group,
            })
    return guests


def import_from_google_csv(file_path: str) -> dict:
    """Parses a Google Contacts CSV file and imports all contacts into Supabase in one call."""
    guests = parse_google_contacts(file_path)
    return import_guests_from_list(guests)


def get_guest_stats() -> dict:
    """Returns the total guest count and a breakdown of how many guests are in each group."""
    rows = db.table("guests").select("group_name").execute().data
    total = len(rows)
    by_group: dict[str, int] = {}
    for row in rows:
        group = row.get("group_name") or "unassigned"
        by_group[group] = by_group.get(group, 0) + 1
    return {"total": total, "by_group": by_group}
