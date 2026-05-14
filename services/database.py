import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
import os

# Streamlit Cloud: /mount/src/ is read-only → use /tmp for writable storage
_DEFAULT_DB = Path("/tmp/coldmail.db") if os.path.exists("/mount/src") else Path(__file__).parent.parent / "coldmail.db"
DB_PATH = Path(os.environ.get("COLDMAIL_DB_PATH", str(_DEFAULT_DB)))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id            TEXT PRIMARY KEY,
            company_name  TEXT NOT NULL,
            industry      TEXT,
            website_url   TEXT,
            email         TEXT,
            email_status  TEXT CHECK(email_status IN ('confirmed','estimated','unknown')),
            url_status    TEXT CHECK(url_status IN ('accessible','inaccessible','needs_review')),
            category      TEXT,
            rank_range    TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS send_history (
            id             TEXT PRIMARY KEY,
            company_id     TEXT REFERENCES companies(id),
            company_name   TEXT,
            category       TEXT,
            sender_name    TEXT,
            sent_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            draft_subject  TEXT,
            language       TEXT DEFAULT 'ko',
            note           TEXT
        );

        CREATE TABLE IF NOT EXISTS templates (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            category      TEXT,
            system_prompt TEXT NOT NULL,
            is_shared     INTEGER DEFAULT 0,
            usage_count   INTEGER DEFAULT 0,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id                  TEXT PRIMARY KEY DEFAULT 'default',
            sender_name         TEXT DEFAULT '',
            sender_title        TEXT DEFAULT '',
            sender_company      TEXT DEFAULT '',
            sender_phone        TEXT DEFAULT '',
            signature_block     TEXT DEFAULT '',
            anthropic_api_key   TEXT DEFAULT '',
            openai_api_key      TEXT DEFAULT '',
            default_language    TEXT DEFAULT 'ko',
            default_category    TEXT DEFAULT ''
        );

        INSERT OR IGNORE INTO user_settings (id) VALUES ('default');
    """)
    conn.commit()
    conn.close()


def new_id():
    return str(uuid.uuid4())


# ── Companies ──────────────────────────────────────────────────────────
def insert_company(data: dict) -> str:
    cid = new_id()
    conn = get_conn()
    conn.execute("""
        INSERT INTO companies (id, company_name, industry, website_url, category, rank_range)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cid, data["company_name"], data.get("industry", ""),
          data.get("website_url", ""), data.get("category", ""), data.get("rank_range", "")))
    conn.commit()
    conn.close()
    return cid


def get_all_companies() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM companies ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_company(cid: str, fields: dict):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [cid]
    conn = get_conn()
    conn.execute(f"UPDATE companies SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_company(cid: str):
    conn = get_conn()
    conn.execute("DELETE FROM companies WHERE id = ?", (cid,))
    conn.commit()
    conn.close()


def clear_companies():
    conn = get_conn()
    conn.execute("DELETE FROM companies")
    conn.commit()
    conn.close()


# ── Send History ────────────────────────────────────────────────────────
def insert_history(data: dict) -> str:
    hid = new_id()
    conn = get_conn()
    conn.execute("""
        INSERT INTO send_history (id, company_id, company_name, category, sender_name, draft_subject, language, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (hid, data.get("company_id", ""), data.get("company_name", ""),
          data.get("category", ""), data.get("sender_name", ""),
          data.get("draft_subject", ""), data.get("language", "ko"), data.get("note", "")))
    conn.commit()
    conn.close()
    return hid


def get_history() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM send_history ORDER BY sent_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_duplicate(company_id: str, days: int = 30) -> bool:
    conn = get_conn()
    row = conn.execute("""
        SELECT id FROM send_history
        WHERE company_id = ?
          AND sent_at >= datetime('now', ?)
        LIMIT 1
    """, (company_id, f"-{days} days")).fetchone()
    conn.close()
    return row is not None


# ── Templates ───────────────────────────────────────────────────────────
def get_templates() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM templates ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_template(data: dict) -> str:
    tid = data.get("id") or new_id()
    conn = get_conn()
    conn.execute("""
        INSERT INTO templates (id, name, category, system_prompt, is_shared, usage_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, category=excluded.category,
            system_prompt=excluded.system_prompt, is_shared=excluded.is_shared,
            updated_at=excluded.updated_at
    """, (tid, data["name"], data.get("category", ""), data["system_prompt"],
          1 if data.get("is_shared") else 0, data.get("usage_count", 0),
          datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return tid


def delete_template(tid: str):
    conn = get_conn()
    conn.execute("DELETE FROM templates WHERE id = ?", (tid,))
    conn.commit()
    conn.close()


def increment_template_usage(tid: str):
    conn = get_conn()
    conn.execute("UPDATE templates SET usage_count = usage_count + 1 WHERE id = ?", (tid,))
    conn.commit()
    conn.close()


# ── User Settings ───────────────────────────────────────────────────────
def get_settings() -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_settings WHERE id = 'default'").fetchone()
    conn.close()
    return dict(row) if row else {}


def save_settings(data: dict):
    fields = {k: v for k, v in data.items() if k != "id"}
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values())
    conn = get_conn()
    conn.execute(f"UPDATE user_settings SET {sets} WHERE id = 'default'", vals)
    conn.commit()
    conn.close()


# ── Dashboard Stats ─────────────────────────────────────────────────────
def get_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM companies WHERE email_status = 'confirmed'").fetchone()[0]
    sent = conn.execute("SELECT COUNT(*) FROM send_history").fetchone()[0]
    pending_url = conn.execute("SELECT COUNT(*) FROM companies WHERE url_status IS NULL").fetchone()[0]
    pending_email = conn.execute("SELECT COUNT(*) FROM companies WHERE email_status IS NULL").fetchone()[0]

    cat_rows = conn.execute("""
        SELECT category, COUNT(*) as cnt FROM send_history GROUP BY category
    """).fetchall()
    category_breakdown = {r["category"]: r["cnt"] for r in cat_rows}

    activity_rows = conn.execute("""
        SELECT 'send' as type, company_name as target, sent_at as ts FROM send_history
        WHERE sent_at >= datetime('now', '-7 days')
        ORDER BY ts DESC LIMIT 20
    """).fetchall()
    conn.close()

    return {
        "total_companies": total,
        "verified_count": verified,
        "sent_count": sent,
        "pending_url": pending_url,
        "pending_email": pending_email,
        "category_breakdown": category_breakdown,
        "recent_activity": [dict(r) for r in activity_rows],
    }
