-- ============================================================================
-- Migration: {{a short description of the change}}
-- Demand:    {{TASK-XXX}} · Author: senior-developer · Date: {{YYYY-MM-DD}}
-- File:      {{new timestamp}}_{{slug}}.sql  (timestamp: date +%Y%m%d%H%M%S)
--
-- DESTRUCTIVENESS ANALYSIS (mandatory — skill migration-safe):
--   {{none — a purely additive change | DETAIL IT: what is altered or removed,
--     the data affected, compatibility with the code running in production}}
--
-- REVERSE ROLLBACK: a commented block at the end (never executed here; it
-- becomes a corrective migration if needed — applied migrations are immutable, H2)
--
-- H3 validates the presence of the statements in FABER_MIGRATION_CHECKS (for
-- Postgres with RLS, the suggested default is: GRANT · RLS · POLICY · search_path).
-- This template is the Postgres + RLS example; adapt it to your project's DBMS
-- while keeping the sections (DDL · functions · RLS/authorization · GRANTs · rollback).
-- ============================================================================

-- 1 ── Main DDL (additive whenever possible)
create table if not exists public.{{table}} (
  id uuid primary key default gen_random_uuid(),
  {{columns}},
  created_at timestamptz not null default now()
);

-- 2 ── Functions: ALWAYS with search_path pinned (anti privilege-escalation).
--      Default: security INVOKER (it runs with the caller's permissions,
--      respecting RLS). Use security DEFINER **only** when the function must
--      cross RLS by design — and in that case, justify it in the ANALYSIS
--      above; a definer with no pinned search_path is a privilege escalation
--      waiting to happen.
create or replace function public.{{fn_name}}()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  {{body}};
  return new;
end;
$$;

-- 3 ── Trigger (if applicable; otherwise remove the section and record it in the analysis)
create trigger {{trg_name}}
  before insert or update on public.{{table}}
  for each row execute function public.{{fn_name}}();

-- 4 ── RLS: ALWAYS enable it + policies per persona (specs 01-DATABASE §RLS)
alter table public.{{table}} enable row level security;

create policy "{{policy_select}}"
  on public.{{table}} for select
  using ({{condition — e.g. auth.uid() = user_id, or the project's role function}});

create policy "{{policy_write}}"
  on public.{{table}} for insert
  with check ({{condition}});

-- 5 ── Minimum GRANTs (never grant all; anonymous roles only when the spec requires it)
grant select on public.{{table}} to {{authenticated_role}};
grant insert on public.{{table}} to {{authenticated_role}};

-- ============================================================================
-- REVERSE ROLLBACK (documentation — DO NOT execute in this migration):
-- drop trigger if exists {{trg_name}} on public.{{table}};
-- drop function if exists public.{{fn_name}}();
-- drop table if exists public.{{table}};
-- ============================================================================
