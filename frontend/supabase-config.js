/* ===========================================================
   MAGIYA — Supabase browser client
   Uses the public anon key (safe to ship in the frontend; row access
   is governed by RLS policies — see migrations/002_wedding_onboarding.sql).
   Requires the supabase-js UMD bundle to be loaded first (CDN <script>).
   =========================================================== */
const SUPABASE_URL = 'https://aohmmxdgihtturoqugih.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvaG1teGRnaWh0dHVyb3F1Z2loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NDMyODcsImV4cCI6MjA5NjExOTI4N30.y1cYJLkoWXIM83Ap1fVuxliWj4VwhegVENsBVlYkz5o';

// `window.supabase` is the global exposed by the supabase-js CDN bundle.
const magiyaSupabase =
  (window.supabase && window.supabase.createClient)
    ? window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;
