import json
from openai import OpenAI
from config.settings import OPENAI_API_KEY
from database.seating import get_all_groups, create_group, assign_guest_to_group

_client = OpenAI(api_key=OPENAI_API_KEY)


def generate_seating_plan(guests: list[dict], groups: list[str], seats_per_table: int = 10) -> list[dict]:
    """
    Asks OpenAI to suggest a seating arrangement.
    Returns a list of {"guest_id": ..., "table_number": ...} dicts.
    """
    prompt = (
        f"You are a wedding seating planner. Arrange the following {len(guests)} guests "
        f"into tables of {seats_per_table} seats each. Try to keep guests from the same group together.\n\n"
        f"Guests (JSON):\n{json.dumps(guests, ensure_ascii=False)}\n\n"
        f"Group names (JSON):\n{json.dumps(groups, ensure_ascii=False)}\n\n"
        'Return ONLY valid JSON in this exact shape: '
        '{"assignments": [{"guest_id": "...", "table_number": 1}, ...]}'
    )
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)["assignments"]


def apply_seating_plan(assignments: list[dict]) -> dict:
    """Saves a generated seating plan to seating_groups + seating_assignments."""
    existing_groups = {g["table_number"]: g["id"] for g in get_all_groups()}
    seat_counters: dict[int, int] = {}
    saved = 0

    for item in assignments:
        table_number = item["table_number"]

        if table_number not in existing_groups:
            group = create_group(group_name=f"Table {table_number}", table_number=table_number)
            existing_groups[table_number] = group["id"]

        seat_counters[table_number] = seat_counters.get(table_number, 0) + 1
        assign_guest_to_group(
            guest_id=item["guest_id"],
            group_id=existing_groups[table_number],
            seat_number=seat_counters[table_number],
        )
        saved += 1

    return {"saved": saved, "tables_used": len(seat_counters)}
