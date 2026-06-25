-- seating_assignments has RLS enabled with no policies (likely a Supabase
-- project default for newly created tables), which silently blocks every
-- write from the anon key the bot and scripts use — found via integration
-- testing (run_seating() failed with "new row violates row-level security
-- policy"). Matches the permissive course-project approach already used
-- for `weddings` in migration 002.

alter table seating_assignments enable row level security;

drop policy if exists "seating_assignments anon all" on seating_assignments;
create policy "seating_assignments anon all" on seating_assignments
    for all to anon using (true) with check (true);
