"""Persistance SQLite (fichier data/credit_horizon.db). Schéma créé et alimenté automatiquement."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import auth
from .analysis import analyze_dossier

BASE = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CH_DB_PATH", BASE / "data" / "credit_horizon.db"))
SEED = json.loads((Path(__file__).parent / "seed.json").read_text(encoding="utf-8"))
_lock = threading.Lock()

SCHEMA = """
create table if not exists users (id integer primary key autoincrement, email text unique not null, name text not null,
  role text not null, password_hash text not null, active integer not null default 1, is_demo integer not null default 0, created_at text not null);
create table if not exists risks (id text primary key, title text not null, category text not null, event text default '', causes text default '',
  consequences text default '', probability integer not null, gravity integer not null, justification text default '', owner text default '',
  control_ids text default '', coso_principles text default '', basis text default 'Constat', recommendation text default '',
  is_demo integer default 0, updated_at text, updated_by text);
create table if not exists risk_history (id integer primary key autoincrement, risk_id text, probability integer, gravity integer, score integer, recorded_at text);
create table if not exists controls (id text primary key, name text, nature text, objective text, risk_ids text, procedure text, owner text,
  supervision text, frequency text, evidence text, indicator text, anomaly_treatment text, status text, last_review text, is_demo integer default 0);
create table if not exists coso_components (id integer primary key, name text, principles text, question text, findings text, gaps text,
  risk_ids text, recommendations text, owner text, indicators text, maturity integer, is_demo integer default 0);
create table if not exists coso_principles (id text primary key, component_id integer, title text, nature text, diagnostic text,
  risk_ids text, assessment text, is_demo integer default 0);
create table if not exists recommendations (id text primary key, risk_id text, coso_gap text, action text, owner text, indicator text,
  basis text, status text, is_demo integer default 0);
create table if not exists actions (id text primary key, priority text, title text, owner text, due text, deliverable text, risk_ids text,
  control_ids text, status text, progress integer, is_demo integer default 0);
create table if not exists anomalies (id text primary key, detected_on text, dossier_ref text, nature text, severity text, risk_id text,
  control_id text, owner text, due_on text, status text, escalation integer, resolution text, declared_by text, is_demo integer default 0);
create table if not exists dossiers (id text primary key, payload text not null, analysis text, status text, created_by text,
  is_demo integer default 0, created_at text, updated_at text);
create table if not exists audit_log (id integer primary key autoincrement, at text, user_email text, action text, entity text, entity_id text, details text);
"""

BUSINESS_TABLES = ["risk_history", "risks", "controls", "coso_principles", "coso_components", "recommendations", "actions", "anomalies", "dossiers"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with _lock, connect() as con:
        con.executescript(SCHEMA)
        if con.execute("select count(*) from users").fetchone()[0] == 0:
            pwd = auth.hash_password(SEED["demo_password"])
            for u in SEED["demo_users"]:
                con.execute("insert into users (email,name,role,password_hash,is_demo,created_at) values (?,?,?,?,1,?)", (u["email"], u["name"], u["role"], pwd, now()))
            _seed_business(con)


def _insert(con, table: str, row: dict) -> None:
    cols = ",".join(row)
    con.execute(f"insert into {table} ({cols}) values ({','.join('?' * len(row))})", list(row.values()))


def _seed_business(con) -> None:
    t = now()
    for r in SEED["risks"]:
        _insert(con, "risks", {**r, "is_demo": 1, "updated_at": t})
        for i, (p, g) in enumerate(SEED["history"].get(r["id"], [])):
            con.execute("insert into risk_history (risk_id,probability,gravity,score,recorded_at) values (?,?,?,?,?)",
                        (r["id"], p, g, p * g, f"{SEED['history_months'][i]}-01T09:00:00+00:00"))
    for c in SEED["controls"]:
        _insert(con, "controls", {**c, "is_demo": 1})
    for c in SEED["coso_components"]:
        _insert(con, "coso_components", {**c, "is_demo": 1})
    for p in SEED["coso_principles"]:
        _insert(con, "coso_principles", {**p, "is_demo": 1})
    for r in SEED["recommendations"]:
        _insert(con, "recommendations", {**r, "is_demo": 1})
    for a in SEED["actions"]:
        _insert(con, "actions", {**a, "is_demo": 1})
    for a in SEED["anomalies"]:
        _insert(con, "anomalies", {**a, "declared_by": "Données de démonstration", "is_demo": 1})
    for d in SEED["dossiers"]:
        payload = {k: v for k, v in d.items() if k != "id"}
        an = analyze_dossier(payload)
        _insert(con, "dossiers", {"id": d["id"], "payload": json.dumps(payload, ensure_ascii=False), "analysis": json.dumps(an, ensure_ascii=False),
                                  "status": an["status"], "created_by": "Données de démonstration", "is_demo": 1, "created_at": t, "updated_at": t})


def reset_demo() -> None:
    with _lock, connect() as con:
        for t in BUSINESS_TABLES:
            con.execute(f"delete from {t}")
        _seed_business(con)


def query(sql: str, params: tuple | list = ()) -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def execute(sql: str, params: tuple | list = ()) -> None:
    with _lock, connect() as con:
        con.execute(sql, params)


def insert(table: str, row: dict) -> None:
    with _lock, connect() as con:
        _insert(con, table, row)


def update(table: str, key: str, row: dict) -> None:
    sets = ",".join(f"{k}=?" for k in row)
    execute(f"update {table} set {sets} where id=?", [*row.values(), key])


def delete(table: str, key) -> None:
    execute(f"delete from {table} where id=?", [key])


def next_id(table: str, prefix: str, pad: int, sep: str = "") -> str:
    n = 0
    for r in query(f"select id from {table} where id like ?", [f"{prefix}{sep}%"]):
        try:
            n = max(n, int(str(r["id"])[len(prefix) + len(sep):]))
        except ValueError:
            pass
    return f"{prefix}{sep}{str(n + 1).zfill(pad)}"


def audit(user: dict | None, action: str, entity: str, entity_id: str = "", details: str = "") -> None:
    execute("insert into audit_log (at,user_email,action,entity,entity_id,details) values (?,?,?,?,?,?)",
            (now(), (user or {}).get("email", "système"), action, entity, entity_id, details[:2000]))
