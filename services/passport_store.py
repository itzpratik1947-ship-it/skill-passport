"""Passport registry with managed Supabase REST storage and SQLite demo fallback.

The Supabase service-role key is used only by this server-side Python module. Never
place it in browser code, a public repository, or a downloadable client bundle.
"""
import json
import os
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()
DB_PATH = Path(os.getenv("SKILL_PASSPORT_DB", "data/passports.sqlite3"))


def _supabase_configured():
    return bool(os.getenv("SUPABASE_URL", "").strip() and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())


def _supabase_request(method, path, **kwargs):
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    headers = kwargs.pop("headers", {})
    headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    response = requests.request(method, f"{base}/rest/v1/{path}", headers=headers, timeout=12, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"Managed Passport database request failed ({response.status_code}). Check Supabase URL, service-role secret, table and policies.")
    return response


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS passports (token TEXT PRIMARY KEY, passport_json TEXT NOT NULL, created_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)")
    con.commit()
    return con


def publish_passport(passport):
    token = secrets.token_urlsafe(24)
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if _supabase_configured():
        _supabase_request("POST", "skill_passports", json={"token": token, "passport_json": passport, "created_at": created, "revoked": False}, headers={"Prefer": "return=minimal"})
    else:
        payload = json.dumps(passport, ensure_ascii=False)
        with _connect() as con:
            con.execute("INSERT INTO passports(token, passport_json, created_at, revoked) VALUES(?,?,?,0)", (token, payload, created))
    return token


def get_public_passport(token):
    if not token or len(token) > 128:
        return None
    if _supabase_configured():
        response = _supabase_request("GET", "skill_passports", params={"token": f"eq.{token}", "revoked": "eq.false", "select": "passport_json", "limit": "1"})
        rows = response.json()
        return rows[0].get("passport_json") if rows and isinstance(rows[0].get("passport_json"), dict) else None
    with _connect() as con:
        row = con.execute("SELECT passport_json FROM passports WHERE token=? AND revoked=0", (token,)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (ValueError, TypeError):
        return None


def revoke_passport(token):
    if not token:
        return False
    if _supabase_configured():
        response = _supabase_request("PATCH", "skill_passports", params={"token": f"eq.{token}", "revoked": "eq.false"}, json={"revoked": True}, headers={"Prefer": "return=representation"})
        return bool(response.json())
    with _connect() as con:
        cur = con.execute("UPDATE passports SET revoked=1 WHERE token=? AND revoked=0", (token,))
        return cur.rowcount > 0


def make_public_url(token, app_url=""):
    base = (app_url or os.getenv("PUBLIC_APP_URL", "")).strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/?passport={quote(token, safe='')}"
