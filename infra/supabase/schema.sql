-- EIS AI — Supabase / Postgres schema
-- Matches Implementation Guidelines §5. Safe to re-run: drops then recreates.

create extension if not exists "pgcrypto";

drop table if exists audit_log cascade;
drop table if exists conversation_messages cascade;
drop table if exists conversation_sessions cascade;
drop table if exists escalation_requests cascade;
drop table if exists attendance cascade;
drop table if exists parent_student_link cascade;
drop table if exists students cascade;
drop table if exists classes cascade;
drop table if exists users cascade;

create table users (
  id uuid primary key default gen_random_uuid(),
  role text not null check (role in ('student','parent','teacher','principal')),
  name text not null,
  email text unique,
  password_hash text not null,        -- mock auth only, not production-grade
  preferred_language text default 'en',
  created_at timestamptz default now()
);

create table classes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  teacher_id uuid references users(id)
);

create table students (
  id uuid primary key references users(id),
  roll_number text not null,
  class_id uuid references classes(id)
);

create table parent_student_link (
  parent_id uuid references users(id),
  student_id uuid references students(id),
  primary key (parent_id, student_id)
);

create table attendance (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id),
  date date not null,
  status text not null check (status in ('present','absent','late')),
  marked_by uuid references users(id),
  marked_at timestamptz default now(),
  unique (student_id, date)
);

create table escalation_requests (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid references users(id),
  target_role text not null check (target_role in ('teacher','management')),
  student_id uuid references students(id),
  reason text,
  status text not null default 'pending' check (status in ('pending','confirmed','completed')),
  created_at timestamptz default now()
);

create table conversation_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  language text default 'en',
  created_at timestamptz default now()
);

create table conversation_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references conversation_sessions(id),
  sender text not null check (sender in ('user','assistant')),
  content text not null,
  intent text,
  created_at timestamptz default now()
);

create table audit_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  action text not null,
  resource text,
  allowed boolean not null,
  created_at timestamptz default now()
);

create index if not exists idx_attendance_student_date on attendance (student_id, date desc);
create index if not exists idx_messages_session on conversation_messages (session_id, created_at);
create index if not exists idx_audit_user on audit_log (user_id, created_at desc);
