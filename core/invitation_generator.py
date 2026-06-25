import base64
from pathlib import Path
from openai import OpenAI
from config.settings import OPENAI_API_KEY_INVITATION

_client = OpenAI(api_key=OPENAI_API_KEY_INVITATION)


def generate_invitation_image(
    bride_name: str,
    groom_name: str,
    wedding_date: str,
    style: str = "elegant",
    colors: str = "white and gold",
    output_path: str = "invitation.png",
) -> str:
    """
    Generates a wedding invitation image using gpt-image-1.
    Saves the image to output_path and returns the path.

    style: "elegant", "rustic", "modern", "floral"
    colors: e.g. "white and gold", "blush pink and ivory", "navy and silver"
    """
    prompt = (
        f"A beautiful {style} wedding invitation card for {bride_name} and {groom_name}, "
        f"wedding date {wedding_date}. Color palette: {colors}. "
        "Elegant floral decorations, decorative borders, couple's names in stylish calligraphy. "
        "High quality, print-ready, no extra text overlays."
    )

    response = _client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )

    image_bytes = base64.b64decode(response.data[0].b64_json)
    Path(output_path).write_bytes(image_bytes)
    return output_path


def build_invitation_params(answers: dict) -> dict:
    """Converts chatbot answers into clean parameters for generate_invitation_image."""
    return {
        "bride_name": answers.get("bride_name", ""),
        "groom_name": answers.get("groom_name", ""),
        "wedding_date": answers.get("wedding_date", ""),
        "style": answers.get("style", "elegant"),
        "colors": answers.get("colors", "white and gold"),
    }
