/* ===========================================================
   MAGIYA — Supabase browser client
   The anon key is intentionally public (read-only by design).
   =========================================================== */
const SUPABASE_URL  = 'https://aohmmxdgihtturoqugih.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvaG1teGRnaWh0dHVyb3F1Z2loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NDMyODcsImV4cCI6MjA5NjExOTI4N30.y1cYJLkoWXIM83Ap1fVuxliWj4VwhegVENsBVlYkz5o';
const db = supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
