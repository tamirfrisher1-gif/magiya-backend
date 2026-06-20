# Contributing to MAGIYA

Welcome to the MAGIYA backend team! Read this document **before writing a single line of code**. It covers how we work together, keep the codebase clean, and avoid stepping on each other's toes.

---

## Ground Rules

- **You never push directly to `main`.** Ever. No exceptions.
- Every change goes through a Pull Request.
- Your PR must be **approved by the project owner** before it can be merged.
- Keep your branch focused on **one feature or fix** at a time.

---

## First-Time Setup

Follow the steps in [README.md](README.md) to:
1. Clone the repo
2. Create and activate your virtual environment
3. Install dependencies
4. Create your `.env` file from `.env.example`
5. Run the bot and confirm `/ping` responds

---

## Branching Strategy

We use the **Feature Branch Workflow**:

```
main                     ← Production-ready. Protected. You cannot push here directly.
  ├── feature/rsvp-flow
  ├── feature/seating-algo
  ├── fix/phone-validation-bug
  └── docs/update-readme
```

### Branch naming convention

| Type | Format | Example |
|---|---|---|
| New feature | `feature/<short-description>` | `feature/rsvp-conversation` |
| Bug fix | `fix/<short-description>` | `fix/dietary-not-saving` |
| Documentation | `docs/<short-description>` | `docs/update-readme` |
| Refactor | `chore/<short-description>` | `chore/extract-rsvp-helper` |

---

## Step-by-Step: How to Contribute

### Step 1 — Sync with main before you start

```bash
git checkout main
git pull origin main
```

### Step 2 — Create your feature branch

```bash
git checkout -b feature/your-feature-name
```

### Step 3 — Write your code

- Work only inside your branch.
- Keep changes focused. Don't refactor unrelated files in the same PR.
- Follow the code style rules below.

### Step 4 — Test your changes locally

```bash
# Run the bot
python main.py

# Run unit tests
pytest tests/test_rsvp_logic.py -v
```

### Step 5 — Stage and commit your work

Write clear, atomic commit messages:

```bash
git add database/guests.py
git commit -m "feat: add get_guest_by_phone function"
```

**Commit message format:** `type: short description`
- `feat:` — new functionality
- `fix:` — bug fix
- `chore:` — maintenance / tooling
- `docs:` — documentation only
- `refactor:` — code restructure, no behavior change

### Step 6 — Push your branch to GitHub

```bash
git push origin feature/your-feature-name
```

### Step 7 — Open a Pull Request

1. Go to the GitHub repository.
2. Click **"Compare & pull request"** on your branch.
3. Fill in the PR form:
   - **Title**: Use the same format as commits (`feat: add rsvp conversation flow`)
   - **Description**: Explain *what* you changed and *why*. Include screenshots or test output if relevant.
4. In **Reviewers**, tag the project owner: `@YOUR_OWNER_USERNAME`
5. Click **"Create pull request"**

### Step 8 — Wait for review

- The project owner will review your code and either **approve**, **request changes**, or **comment**.
- If changes are requested, push new commits to the same branch — the PR updates automatically.
- **Do not merge your own PR.** Only the project owner merges.

### Step 9 — After your PR is merged

```bash
git checkout main
git pull origin main
git branch -d feature/your-feature-name  # clean up locally
```

---

## Code Style

| Rule | Detail |
|---|---|
| Formatter | Follow PEP 8 |
| Type hints | Required on all function signatures |
| Comments | Only when the *why* is non-obvious |
| Docstrings | Short one-liner for public functions |
| Line length | Max 100 characters |

Good example:
```python
def get_guest_by_phone(phone: str) -> Optional[dict]:
    """Returns the guest row or None if not found."""
    response = db.table("guests").select("*").eq("phone", phone).maybe_single().execute()
    return response.data
```

---

## What Goes Where

| You're working on... | Edit files in... |
|---|---|
| Bot commands (/start, /ping, etc.) | `bot_handlers/commands.py` |
| Multi-step conversation flows | `bot_handlers/rsvp_flow.py` |
| Admin/dashboard commands | `bot_handlers/admin.py` |
| Supabase guest table operations | `database/guests.py` |
| Supabase RSVP table operations | `database/rsvps.py` |
| Supabase seating table operations | `database/seating.py` |
| Business logic / validation | `core/rsvp_logic.py` |
| AI seating algorithm | `core/seating_algorithm.py` |
| AI invitation generator | `core/invitation_generator.py` |
| App config / secrets | `config/settings.py` |

**Do not** put business logic inside `bot_handlers/`. Handlers should be thin — call functions from `core/` or `database/`.

---

## PR Checklist

Before requesting a review, confirm:

- [ ] My branch is up to date with `main` (`git pull origin main`)
- [ ] The bot starts without errors (`python main.py`)
- [ ] Unit tests pass (`pytest tests/test_rsvp_logic.py -v`)
- [ ] I haven't committed `.env` or any real tokens
- [ ] My PR title follows the `type: description` format
- [ ] I tagged the project owner as a reviewer

---

## Questions?

Open a GitHub Issue or message the project owner directly.
