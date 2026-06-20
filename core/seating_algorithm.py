import json
from openai import OpenAI
from config.settings import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)


def generate_seating_plan(guests: list[dict], groups: list[dict], seats_per_table: int = 10) -> dict:
    """
    Asks OpenAI to suggest a seating arrangement.
    Returns a dict mapping guest_id → table_number.
    """
    prompt = (
        f"You are a wedding seating planner. Arrange the following {len(guests)} guests "
        f"into tables of {seats_per_table} seats each. Try to keep guests from the same group together.\n\n"
        f"Guests (JSON):\n{json.dumps(guests, ensure_ascii=False)}\n\n"
        f"Groups (JSON):\n{json.dumps(groups, ensure_ascii=False)}\n\n"
        "Return ONLY valid JSON: a list of objects with keys guest_id and table_number."
    )
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
