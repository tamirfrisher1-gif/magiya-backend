-- Run this in the Supabase SQL Editor (Project → SQL Editor → New query)
-- Creates the weddings, groups, and seating_assignments tables
-- and adds wedding_id to the existing guests table.

-- 1. Weddings — one row per couple
create table if not exists weddings (
    id           text primary key,          -- e.g. "sarah-et-david-15-08-2026"
    bride_name   text not null,
    groom_name   text not null,
    wedding_date date not null,
    table_capacity int not null default 10  -- seats per table at the venue
);

-- 2. Groups — custom group names defined by the couple
create table if not exists groups (
    id          uuid primary key default gen_random_uuid(),
    wedding_id  text not null references weddings(id) on delete cascade,
    name        text not null,
    unique (wedding_id, name)
);

-- 3. Add wedding_id to existing guests table
alter table guests
    add column if not exists wedding_id text references weddings(id) on delete cascade;

-- 4. Seating assignments — output of the algorithm
create table if not exists seating_assignments (
    id           uuid primary key default gen_random_uuid(),
    wedding_id   text not null references weddings(id) on delete cascade,
    guest_phone  text not null references guests(phone) on delete cascade,
    table_number int  not null,
    unique (wedding_id, guest_phone)
);
