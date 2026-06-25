-- Run this in the Supabase SQL Editor (Project → SQL Editor → New query).
-- Adds the onboarding fields used by the sign-up page and enables RLS so the
-- public anon key (used by the browser sign-up form) can create/read weddings.

-- 1. Onboarding fields on the existing weddings table
alter table weddings add column if not exists contact_email text;  -- couple's email (Google contacts)
alter table weddings add column if not exists venue         text;  -- venue name

-- 2. Row Level Security for the browser sign-up form.
--    Course-project policies: permissive. Tighten before any public deploy
--    (e.g. scope to authenticated users, or move writes behind the API).
alter table weddings enable row level security;

drop policy if exists "weddings anon select" on weddings;
create policy "weddings anon select" on weddings
    for select to anon using (true);

drop policy if exists "weddings anon insert" on weddings;
create policy "weddings anon insert" on weddings
    for insert to anon with check (true);

drop policy if exists "weddings anon update" on weddings;
create policy "weddings anon update" on weddings
    for update to anon using (true) with check (true);
