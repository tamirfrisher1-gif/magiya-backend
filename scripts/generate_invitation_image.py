"""
Generates one wedding invitation image via OpenAI and saves it to
assets/invitation.png. Run this once (or whenever you want a new design) —
the bot then reuses this saved file for every guest's RSVP greeting instead
of generating a fresh (paid, slower) image per guest.

Requires OPENAI_API_KEY_INVITATION in .env (see core/invitation_generator.py).

Run with: python scripts/generate_invitation_image.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.invitation_generator import generate_invitation_image
from core.wedding_config import COUPLE_NAME_1, COUPLE_NAME_2, WEDDING_DATE

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "invitation.png"


def main() -> None:
    print(f"Generating invitation image for {COUPLE_NAME_1} & {COUPLE_NAME_2}...")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    generate_invitation_image(
        bride_name=COUPLE_NAME_1,
        groom_name=COUPLE_NAME_2,
        wedding_date=WEDDING_DATE,
        output_path=str(OUTPUT_PATH),
    )

    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
