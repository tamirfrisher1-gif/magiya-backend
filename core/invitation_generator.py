import base64
from openai import OpenAI


def _client() -> OpenAI:
    from config.settings import OPENAI_API_KEY_INVITATION, OPENAI_API_KEY
    return OpenAI(api_key=OPENAI_API_KEY_INVITATION or OPENAI_API_KEY)


def generate_invitation_image_b64(
    bride_name: str,
    groom_name: str,
    wedding_date: str = "",
    style: str = "elegant",
    colors: str = "white and gold",
    elements: str = "",
) -> str:
    """Call gpt-image-1 and return a base64 data URL (data:image/png;base64,...)."""
    date_part = f", wedding date {wedding_date}" if wedding_date else ""
    elements_part = f" Include: {elements}." if elements else ""
    prompt = (
        f"A beautiful {style} wedding invitation card for {bride_name} and {groom_name}"
        f"{date_part}. Color palette: {colors}.{elements_part} "
        "Elegant floral decorations, decorative borders, couple names in stylish calligraphy. "
        "High quality, print-ready, no extra text overlays."
    )
    response = _client().images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )
    return f"data:image/png;base64,{response.data[0].b64_json}"


def build_invitation_params(answers: dict) -> dict:
    return {
        "bride_name": answers.get("bride_name", ""),
        "groom_name": answers.get("groom_name", ""),
        "wedding_date": answers.get("wedding_date", ""),
        "style": answers.get("style", "elegant"),
        "colors": answers.get("colors", "white and gold"),
        "elements": answers.get("elements", ""),
    }
