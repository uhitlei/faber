-- ============================================================================
-- Migration: {{descrição curta da mudança}}
-- Demanda:   {{TASK-XXX}} · Autor: senior-developer · Data: {{AAAA-MM-DD}}
-- Arquivo:   {{timestamp novo}}_{{slug}}.sql  (timestamp: date +%Y%m%d%H%M%S)
--
-- ANÁLISE DE DESTRUTIVIDADE (obrigatória — Skill migration-safe):
--   {{nenhuma — mudança puramente aditiva | DETALHAR: o que é alterado/
--     removido, dados afetados, compatibilidade com o código em produção}}
--
-- ROLLBACK REVERSO: bloco comentado ao final (nunca executado aqui; vira
-- migration corretiva se necessário — migrations aplicadas são imutáveis, H2)
--
-- H3 valida a presença dos termos de FABER_MIGRATION_CHECKS (para Postgres
-- com RLS, o padrão sugerido é: GRANT · RLS · POLICY · search_path).
-- Este template é o exemplo Postgres+RLS; adapte ao SGBD do projeto mantendo
-- as seções (DDL · funções · RLS/autorização · GRANTs · rollback).
-- ============================================================================

-- 1 ── DDL principal (aditivo sempre que possível)
create table if not exists public.{{tabela}} (
  id uuid primary key default gen_random_uuid(),
  {{colunas}},
  created_at timestamptz not null default now()
);

-- 2 ── Funções: SEMPRE com search_path fixado (anti privilege-escalation).
--      Padrão: security INVOKER (roda com as permissões de quem chama,
--      respeitando RLS). Use security DEFINER **apenas** quando a função
--      precisa atravessar RLS por desenho — e, nesse caso, justifique na
--      ANÁLISE acima; definer sem search_path fixado é escalação de
--      privilégio esperando para acontecer.
create or replace function public.{{fn_nome}}()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  {{corpo}};
  return new;
end;
$$;

-- 3 ── Trigger (se aplicável; senão, remover a seção e registrar na análise)
create trigger {{trg_nome}}
  before insert or update on public.{{tabela}}
  for each row execute function public.{{fn_nome}}();

-- 4 ── RLS: habilitar SEMPRE + policies por perfil (specs 01-DATABASE §RLS)
alter table public.{{tabela}} enable row level security;

create policy "{{policy_select}}"
  on public.{{tabela}} for select
  using ({{condição — ex.: auth.uid() = user_id ou função de papel do projeto}});

create policy "{{policy_write}}"
  on public.{{tabela}} for insert
  with check ({{condição}});

-- 5 ── GRANTs mínimos (nunca grant all; papéis anônimos só quando a spec exigir)
grant select on public.{{tabela}} to {{papel_autenticado}};
grant insert on public.{{tabela}} to {{papel_autenticado}};

-- ============================================================================
-- ROLLBACK REVERSO (documentação — NÃO executar nesta migration):
-- drop trigger if exists {{trg_nome}} on public.{{tabela}};
-- drop function if exists public.{{fn_nome}}();
-- drop table if exists public.{{tabela}};
-- ============================================================================
