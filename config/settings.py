import os
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = {
    "TELEGRAM_BOT_TOKEN": "Get this from @BotFather on Telegram",
    "SUPABASE_URL": "Found in Supabase Dashboard → Project Settings → API",
    "SUPABASE_KEY": "Found in Supabase Dashboard → Project Settings → API",
    "OPENAI_API_KEY": "Found in platform.openai.com → API Keys",
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
