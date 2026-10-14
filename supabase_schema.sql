-- Run this in the Supabase SQL Editor for durable public Passport snapshots.
-- Keep SUPABASE_SERVICE_ROLE_KEY only in server-side Streamlit secrets/environment variables.
create table if not exists public.skill_passports (
    token text primary key,
    passport_json jsonb not null,
    created_at timestamptz not null default now(),
    revoked boolean not null default false
);

create index if not exists skill_passports_active_created_idx
    on public.skill_passports (revoked, created_at desc);

-- Do not enable anonymous table access. The Streamlit server accesses this table
-- using its server-side service-role key. Never put that key in client-side code.
revoke all on table public.skill_passports from anon, authenticated;
