from openai import OpenAI
from config.settings import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)


def generate_invitation(
    guest_name: str,
    couple_names: str,
    wedding_date: str,
    venue: str,
    tone: str = "warm and elegant",
) -> str:
    """Generates a personalized wedding invitation message via OpenAI."""
    prompt = (
        f"Write a personalized wedding invitation in Hebrew for a guest named {guest_name}.\n"
        f"The couple: {couple_names}\n"
        f"Date: {wedding_date}\n"
        f"Venue: {venue}\n"
        f"Tone: {tone}\n"
        "Keep it under 5 sentences. Do not add a subject line."
    )
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()
