-- The seating_assignments table was accidentally rebuilt with a different
-- structure (guest_id/group_id/seat_number) by someone unaware of migration
-- 001_seating_schema.sql's wedding_id/guest_phone/table_number design.
-- Restoring the original design here, with ON DELETE CASCADE added so
-- removing a guest or wedding cleans up their seating row automatically
-- (a real bug found via integration testing — without this, deleting a
-- guest who already has a seating assignment fails with a foreign key
-- violation).

DROP TABLE IF EXISTS seating_assignments;

CREATE TABLE seating_assignments (
    id           uuid primary key default gen_random_uuid(),
    wedding_id   text not null references weddings(id) on delete cascade,
    guest_phone  text not null references guests(phone) on delete cascade,
    table_number int  not null,
    unique (wedding_id, guest_phone)
);
