from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from config.settings import GOOGLE_WEB_CLIENT_ID, GOOGLE_WEB_CLIENT_SECRET, GOOGLE_REDIRECT_URI

SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_WEB_CLIENT_ID,
        "client_secret": GOOGLE_WEB_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [GOOGLE_REDIRECT_URI],
    }
}


def _new_flow() -> Flow:
    return Flow.from_client_config(_CLIENT_CONFIG, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)


def get_auth_url(state: str = "") -> str:
    """Returns the Google OAuth URL to redirect the browser to for contact access.
    `state` round-trips through Google back to our callback (we use it to carry
    the wedding_id so imported contacts can be tagged to the right wedding)."""
    flow = _new_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", state=state)
    return auth_url


def fetch_google_contacts(code: str) -> list[dict]:
    """Exchanges the OAuth code for a token, then fetches all contacts from Google People API."""
    flow = _new_flow()
    flow.fetch_token(code=code)
    service = build("people", "v1", credentials=flow.credentials)

    contacts = []
    next_page_token = None

    while True:
        result = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=1000,
                personFields="names,phoneNumbers",
                pageToken=next_page_token,
            )
            .execute()
        )
        contacts.extend(result.get("connections", []))
        next_page_token = result.get("nextPageToken")
        if not next_page_token:
            break

    return contacts


def contacts_to_guests(contacts: list[dict]) -> list[dict]:
    """Converts raw Google People API contacts into the guest format for import_guests_from_list.
    Only keeps name and phone — the couple will classify groups themselves via the UI."""
    guests: list[dict] = []
    for contact in contacts:
        names = contact.get("names", [])
        phones = contact.get("phoneNumbers", [])

        if not phones:
            continue

        full_name = names[0].get("displayName", "Unknown") if names else "Unknown"
        phone = phones[0].get("canonicalForm") or phones[0].get("value", "")

        guests.append({
            "full_name": full_name,
            "phone": phone,
        })

    return guests
