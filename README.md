# MAGIYA — Smart Wedding Guest Management Platform

> No spreadsheets. No manual tracking. No middlemen.

MAGIYA is an AI-powered wedding planning backend. It automates guest invitations, RSVP collection, dietary tracking, seating arrangement, and provides a real-time event-day dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Telegram Bot | `python-telegram-bot` v21 (async) |
| Database | Supabase (PostgreSQL + Realtime) |
| AI | OpenAI API (invitations + seating) |
| Secrets | `python-dotenv` |

---

## Project Structure

```
magiya-backend/
├── main.py                  ← Entry point — starts the Telegram bot
├── requirements.txt
├── .env.example             ← Template for secrets (never commit .env)
│
├── config/
│   └── settings.py          ← Loads and validates all environment variables
│
├── database/
│   ├── client.py            ← Supabase client singleton
│   ├── guests.py            ← CRUD for guests table
│   ├── rsvps.py             ← CRUD for rsvps table
│   └── seating.py           ← CRUD for seating tables
│
├── bot_handlers/
│   ├── commands.py          ← /start, /ping, /help
│   ├── rsvp_flow.py         ← Multi-step RSVP conversation
│   └── admin.py             ← /stats dashboard command
│
├── core/
│   ├── rsvp_logic.py        ← Business logic / validation helpers
│   ├── seating_algorithm.py ← AI-powered seating via OpenAI
│   └── invitation_generator.py ← AI invitation text via OpenAI
│
└── tests/
    ├── test_rsvp_logic.py   ← Unit tests (no DB needed)
    └── test_database.py     ← Integration tests (needs Supabase)
```

---

## Local Setup (First Time)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_ORG/magiya-backend.git
cd magiya-backend
```

### 2. Create a virtual environment

```bash
# Create the venv (do this once)
python -m venv venv

# Activate it — Windows
venv\Scripts\activate

# Activate it — macOS / Linux
source venv/bin/activate
```

> You should see `(venv)` at the start of your terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your environment variables

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Now open `.env` in your editor and fill in the four values:

```env
TELEGRAM_BOT_TOKEN=   ← From @BotFather on Telegram
SUPABASE_URL=         ← Supabase Dashboard → Project Settings → API → Project URL
SUPABASE_KEY=         ← Supabase Dashboard → Project Settings → API → anon/public key
OPENAI_API_KEY=       ← platform.openai.com → API Keys
```

**IMPORTANT:** `.env` is listed in `.gitignore`. It will never be committed. Never share it or paste it anywhere.

### 5. Set up the database

Open your Supabase project dashboard → SQL Editor, and run the following schema:

```sql
create table guests (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  phone text unique not null,
  group_name text,
  invited_at timestamptz default now()
);

create table rsvps (
  id uuid primary key default gen_random_uuid(),
  guest_id uuid references guests(id),
  status text check (status in ('confirmed','declined','pending')) default 'pending',
  party_size int default 1,
  dietary_restrictions text,
  responded_at timestamptz
);

create table seating_groups (
  id uuid primary key default gen_random_uuid(),
  group_name text not null,
  table_number int
);

create table seating_assignments (
  id uuid primary key default gen_random_uuid(),
  guest_id uuid references guests(id),
  group_id uuid references seating_groups(id),
  seat_number int
);
```

### 6. Run the bot

```bash
python main.py
```

You should see:
```
INFO - MAGIYA bot is starting...
```

Open Telegram, find your bot, and send:
- `/ping` → Bot replies: **"Pong! MAGIYA bot is alive 🎉"**
- `/start` → Bot replies with a welcome message

---

## Running Tests

```bash
# Unit tests only (no database required)
pytest tests/test_rsvp_logic.py -v

# All tests including database integration (requires .env with real Supabase credentials)
pytest tests/ -v
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full branching strategy and pull request guide.
