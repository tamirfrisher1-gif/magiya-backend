from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY

# Single shared client — import `db` anywhere in the project
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
