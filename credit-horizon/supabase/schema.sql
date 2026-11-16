-- Schéma CRÉDIT HORIZON RISK INTELLIGENCE (à exécuter dans l'éditeur SQL Supabase si souhaité ;
-- l'application le crée aussi automatiquement au premier démarrage)
create table if not exists users (
  id serial primary key,
  email text unique not null,
  name text not null,
  role text not null check (role in ('admin','directeur','analyste','commercial','controleur')),
  password_hash text not null,
  active boolean not null default true,
  is_demo boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists risks (
  id text primary key,
  title text not null,
  category text not null,
  event text not null default '',
  causes text not null default '',
  consequences text not null default '',
  probability int not null check (probability between 1 and 5),
  gravity int not null check (gravity between 1 and 5),
  justification text not null default '',
  owner text not null default '',
  control_ids text not null default '',
  coso_principles text not null default '',
  basis text not null default 'Constat',
  recommendation text not null default '',
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text
);
create table if not exists risk_history (
  id serial primary key,
  risk_id text not null,
  probability int not null,
  gravity int not null,
  score int not null,
  recorded_at timestamptz not null default now(),
  is_demo boolean not null default false
);
create table if not exists controls (
  id text primary key,
  name text not null,
  nature text not null default 'Préventif',
  objective text not null default '',
  risk_ids text not null default '',
  procedure text not null default '',
  owner text not null default '',
  supervision text not null default '',
  frequency text not null default '',
  evidence text not null default '',
  indicator text not null default '',
  anomaly_treatment text not null default '',
  status text not null default 'À concevoir',
  last_review text,
  is_demo boolean not null default false,
  updated_at timestamptz not null default now()
);
create table if not exists coso_components (
  id int primary key,
  name text not null,
  principles text not null,
  question text not null default '',
  findings text not null default '',
  gaps text not null default '',
  risk_ids text not null default '',
  recommendations text not null default '',
  owner text not null default '',
  indicators text not null default '',
  maturity int not null default 1 check (maturity between 1 and 5),
  is_demo boolean not null default false,
  updated_at timestamptz not null default now()
);
create table if not exists coso_principles (
  id text primary key,
  component_id int not null,
  title text not null,
  nature text not null default 'Hypothèse à vérifier',
  diagnostic text not null default '',
  risk_ids text not null default '',
  assessment text not null default 'Non évalué',
  is_demo boolean not null default false,
  updated_at timestamptz not null default now()
);
create table if not exists recommendations (
  id text primary key,
  risk_id text not null,
  coso_gap text not null default '',
  action text not null default '',
  owner text not null default '',
  indicator text not null default '',
  basis text not null default 'Constat',
  status text not null default 'À lancer',
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists actions (
  id text primary key,
  priority text not null default 'P2',
  title text not null,
  owner text not null default '',
  due text not null default '',
  deliverable text not null default '',
  risk_ids text not null default '',
  control_ids text not null default '',
  status text not null default 'À faire',
  progress int not null default 0 check (progress between 0 and 100),
  is_demo boolean not null default false,
  updated_at timestamptz not null default now()
);
create table if not exists anomalies (
  id text primary key,
  detected_on text not null,
  dossier_ref text not null default '',
  nature text not null,
  severity text not null default 'Significative',
  risk_id text not null default '',
  control_id text not null default '',
  owner text not null default '',
  due_on text not null default '',
  status text not null default 'Ouverte',
  escalation int not null default 1 check (escalation between 1 and 3),
  resolution text not null default '',
  declared_by text not null default '',
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists dossiers (
  id text primary key,
  company jsonb not null default '{}'::jsonb,
  request jsonb not null default '{}'::jsonb,
  financials jsonb not null default '{}'::jsonb,
  documents jsonb not null default '{}'::jsonb,
  guarantees jsonb not null default '{}'::jsonb,
  observations text not null default '',
  analysis jsonb,
  status text not null default 'Brouillon',
  created_by text not null default '',
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists audit_log (
  id serial primary key,
  at timestamptz not null default now(),
  user_email text not null,
  action text not null,
  entity text not null,
  entity_id text not null default '',
  details text not null default ''
);
create index if not exists idx_history_risk on risk_history(risk_id, recorded_at);
create index if not exists idx_audit_at on audit_log(at desc);
