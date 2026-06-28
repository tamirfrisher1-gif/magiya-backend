import os
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = {
    "TELEGRAM_BOT_TOKEN": "Get this from @BotFather on Telegram",
    "SUPABASE_URL": "Found in Supabase Dashboard → Project Settings → API",
    "SUPABASE_KEY": "Found in Supabase Dashboard → Project Settings → API",
    "OPENAI_API_KEY": "Found in platform.openai.com → API Keys",
    "GOOGLE_CLIENT_ID": "Found in Google Cloud Console → APIs & Services → Credentials",
    "GOOGLE_CLIENT_SECRET": "Found in Google Cloud Console → APIs & Services → Credentials",
}

_missing = [k for k in _REQUIRED if not os.getenv(k)]
if _missing:
    lines = "\n".join(f"  {k}: {_REQUIRED[k]}" for k in _missing)
    raise EnvironmentError(
        f"Missing required environment variables:\n{lines}\n"
        "Copy .env.example to .env and fill in the values."
    )

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET: str = os.environ["GOOGLE_CLIENT_SECRET"]
OPENAI_API_KEY_INVITATION: str = os.getenv("OPENAI_API_KEY_INVITATION", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
GOOGLE_WEB_CLIENT_ID: str = os.getenv("GOOGLE_WEB_CLIENT_ID", "")
GOOGLE_WEB_CLIENT_SECRET: str = os.getenv("GOOGLE_WEB_CLIENT_SECRET", "")

GOOGLE_REDIRECT_URI: str = os.getenv(
    "GOOGLE_REDIRECT_URI", "https://magiya-api.onrender.com/auth/google/callback"
)
FRONTEND_GUESTLIST_URL: str = os.getenv(
    "FRONTEND_GUESTLIST_URL", "https://phenomenal-dragon-c76a9d.netlify.app/guestlist.html"
)
