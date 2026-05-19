-- Phase 1: migrate packets id/user_id text→uuid, timestamps text→timestamptz
-- Handles both branch (no table) and production (existing table with 31 rows).

do $$ begin
  if not exists (
    select from information_schema.tables
    where table_schema = 'public' and table_name = 'packets'
  ) then
    execute '
      create table public.packets (
        id                  uuid primary key default gen_random_uuid(),
        user_id             uuid references public.users(id) on delete set null,
        packet_type         text not null,
        language            text not null,
        county              text not null,
        fee_usd             numeric not null,
        zip_path            text not null,
        status              text not null default ''pending_payment'',
        confirmation_number text,
        filed_at            timestamptz,
        paid_at             timestamptz,
        created_at          timestamptz not null default now()
      )';
    execute 'alter table public.packets enable row level security';
  else
    execute 'alter table public.packets drop constraint packets_pkey';
    execute 'alter table public.packets
      alter column id type uuid using id::uuid,
      alter column id set default gen_random_uuid()';
    execute 'alter table public.packets add primary key (id)';
    execute 'alter table public.packets alter column user_id drop not null';
    execute 'update public.packets
      set user_id = null
      where user_id !~ ''^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$''';
    execute 'alter table public.packets
      alter column user_id type uuid using user_id::uuid';
    execute 'alter table public.packets
      add constraint packets_user_id_fkey
      foreign key (user_id) references public.users(id) on delete set null';
    execute 'alter table public.packets
      alter column created_at type timestamptz using created_at::timestamptz,
      alter column created_at set default now(),
      alter column filed_at   type timestamptz using filed_at::timestamptz,
      alter column paid_at    type timestamptz using paid_at::timestamptz';
  end if;
end $$;

create index if not exists idx_packets_user   on public.packets(user_id);
create index if not exists idx_packets_status on public.packets(status);
