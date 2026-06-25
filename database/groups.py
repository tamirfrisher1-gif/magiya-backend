from database.client import db


def create_group(wedding_id: str, name: str) -> dict:
    """Creates a new guest group for a wedding (e.g. 'Famille côté marié')."""
    response = (
        db.table("groups")
        .upsert({"wedding_id": wedding_id, "name": name}, on_conflict="wedding_id,name")
        .execute()
    )
    return response.data[0]


def get_groups(wedding_id: str) -> list[str]:
    """Returns all group names defined for a wedding, sorted alphabetically."""
    rows = (
        db.table("groups").select("name").eq("wedding_id", wedding_id).execute().data
    )
    return sorted(row["name"] for row in rows)


def delete_group(wedding_id: str, name: str) -> None:
    """Removes a group from a wedding."""
    db.table("groups").delete().eq("wedding_id", wedding_id).eq("name", name).execute()
