# MAGIYA Dashboard API

A small FastAPI service that serves aggregated guest & RSVP statistics as JSON,
so the frontend can build the dashboard UI on top of a stable contract.

## Run

```bash
# from the magiya-backend/ root, with the venv active
uvicorn api.main:app --reload --port 8001
```

- Interactive docs / schema: http://localhost:8001/docs
- Health check: `GET /health` → `{"status": "ok"}`

## Endpoint

### `GET /dashboard`

Returns the full aggregated payload:

```json
{
  "summary": {
    "invited": 5,
    "confirmed": 2,
    "declined": 1,
    "no_response": 2,
    "expected_headcount": 5
  },
  "status_breakdown": { "confirmed": 2, "declined": 1, "pending": 2 },
  "by_group": [
    { "group": "Unassigned", "invited": 1, "confirmed": 0, "expected": 0 },
    { "group": "family",  "invited": 2, "confirmed": 1, "expected": 2 },
    { "group": "friends", "invited": 2, "confirmed": 1, "expected": 3 }
  ],
  "recent_updates": [
    { "name": "Dan", "group": "friends", "status": "pending",
      "party_size": 0, "responded_at": "2026-06-23T10:00:00Z" }
  ]
}
```

### Field notes
- `no_response` = guests with no RSVP row **plus** RSVPs whose status is `pending`.
- `expected_headcount` = sum of `party_size` over confirmed RSVPs.
- `by_group` is sorted alphabetically; guests with no group fall under `"Unassigned"`.
- `recent_updates` = the 10 most recent responses (by `responded_at`), newest first.
  `party_size` is `0` for non-confirmed statuses.
- On a database/connection failure the endpoint returns HTTP `502` with a `detail` message.

## Architecture
- `core/dashboard.py` — pure aggregation logic (`build_dashboard`), no I/O, unit-tested.
- `database/dashboard.py` — fetches guests + rsvps from Supabase, delegates to `build_dashboard`.
- `api/main.py` — FastAPI app, CORS, Pydantic response models, the `/dashboard` and `/health` routes.

## CORS
Currently open to all origins (`*`) for the course project. Restrict
`allow_origins` in `api/main.py` to the real frontend origin before any public deploy.
