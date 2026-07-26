import sqlite3
import hashlib
import secrets
import os
from pathlib import Path
from datetime import datetime, timedelta


DB_PATH = Path(__file__).parent.parent / "data" / "bart.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TOKEN_EXPIRY_DAYS = 30
ACCOUNT_EXPIRY_DAYS = 30

_DATABASE_URL = os.environ.get("DATABASE_URL")


def _is_pg():
    return bool(_DATABASE_URL)


def _get_db():
    if _is_pg():
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(_DATABASE_URL)
        conn.autocommit = False
        return conn
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _P():
    return "%s" if _is_pg() else "?"


def _NOW():
    return "NOW()" if _is_pg() else "datetime('now')"


def _exec(conn, sql, params=None):
    if _is_pg():
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description:
                return cur.fetchall()
            return None
    else:
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)


def _exec_script(conn, script):
    if _is_pg():
        with conn.cursor() as cur:
            cur.execute(script)
    else:
        conn.executescript(script)


def _fetchone(conn, sql, params=None):
    if _is_pg():
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    else:
        row = conn.execute(sql, params or ()).fetchone()
        return dict(row) if row else None


def _fetchall(conn, sql, params=None):
    if _is_pg():
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    else:
        rows = conn.execute(sql, params or ()).fetchall()
        return [dict(r) for r in rows]


def _row_to_dict(row):
    if _is_pg():
        return dict(row) if row else None
    return dict(row) if row else None


def _commit(conn):
    conn.commit()


def _close(conn):
    conn.close()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    salt, hsh = stored.split(":", 1)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex() == hsh


def init_db():
    conn = _get_db()
    p = _P()
    if _is_pg():
        _exec_script(conn, """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT NOW(),
                activated_at TEXT,
                banned INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS activation_codes (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT NOW(),
                used_at TEXT
            );
        """)
        try:
            _exec(conn, "ALTER TABLE users ADD COLUMN IF NOT EXISTS activated_at TEXT")
        except Exception:
            pass
    else:
        _exec_script(conn, f"""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT ({_NOW()}),
                activated_at TEXT,
                banned INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ({_NOW()}),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS activation_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT ({_NOW()}),
                used_at TEXT
            );
        """)
        try:
            _exec(conn, "ALTER TABLE users ADD COLUMN activated_at TEXT")
        except Exception:
            pass
    _commit(conn)
    _close(conn)


def seed_admin():
    conn = _get_db()
    p = _P()
    existing = _fetchone(conn, f"SELECT id FROM users WHERE email = {p}", ("admin@bart.ai",))
    if not existing:
        pw = _hash_password("admin123")
        _exec(conn, f"INSERT INTO users (email, password, name, role, activated_at) VALUES ({p}, {p}, {p}, {p}, {_NOW()})",
              ("admin@bart.ai", pw, "Admin", "admin"))
        _commit(conn)
        print("Default admin account: admin@bart.ai / admin123")
    else:
        _exec(conn, f"UPDATE users SET activated_at = {_NOW()} WHERE email = {p} AND activated_at IS NULL",
              ("admin@bart.ai",))
        _commit(conn)
    _close(conn)


def register_with_code(email: str, password: str, code: str, name: str = "") -> dict:
    email = email.lower().strip()
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not code:
        return {"success": False, "error": "Activation code is required."}

    conn = _get_db()
    p = _P()
    existing = _fetchone(conn, f"SELECT id FROM users WHERE email = {p}", (email,))
    if existing:
        _close(conn)
        return {"success": False, "error": "Email already registered."}

    row = _fetchone(conn, f"SELECT id, used FROM activation_codes WHERE code = {p}", (code.strip(),))
    if not row:
        _close(conn)
        return {"success": False, "error": "Invalid activation code."}
    if row["used"]:
        _close(conn)
        return {"success": False, "error": "Activation code already used."}

    pw = _hash_password(password)
    _exec(conn, f"INSERT INTO users (email, password, name, activated_at) VALUES ({p}, {p}, {p}, {_NOW()})",
          (email, pw, name.strip()))
    _exec(conn, f"UPDATE activation_codes SET used = 1, used_at = {_NOW()} WHERE id = {p}", (row["id"],))
    _commit(conn)
    _close(conn)
    return {"success": True, "message": "Account created successfully!"}


def _is_account_expired(activated_at) -> bool:
    if not activated_at:
        return True
    if isinstance(activated_at, datetime):
        act = activated_at
    else:
        try:
            act = datetime.fromisoformat(activated_at)
        except (ValueError, TypeError):
            return True
    return datetime.utcnow() - act > timedelta(days=ACCOUNT_EXPIRY_DAYS)


def login_user(email: str, password: str) -> dict:
    conn = _get_db()
    p = _P()
    user = _fetchone(conn, f"SELECT id, email, password, name, role, banned, activated_at FROM users WHERE email = {p}",
                     (email.lower().strip(),))
    _close(conn)

    if not user:
        return {"success": False, "error": "Invalid email or password."}
    if user["banned"]:
        return {"success": False, "error": "Account is disabled."}
    if not _verify_password(password, user["password"]):
        return {"success": False, "error": "Invalid email or password."}
    if user["role"] != "admin" and _is_account_expired(user["activated_at"]):
        return {"success": False, "error": f"Account expired. Contact admin to reactivate (valid for {ACCOUNT_EXPIRY_DAYS} days)."}

    token = secrets.token_hex(32)
    expires = (datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS)).isoformat()

    conn = _get_db()
    _exec(conn, f"INSERT INTO tokens (user_id, token, expires_at) VALUES ({p}, {p}, {p})",
          (user["id"], token, expires))
    _commit(conn)
    _close(conn)

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
    }


def validate_token(token: str) -> dict | None:
    if not token:
        return None
    conn = _get_db()
    p = _P()
    row = _fetchone(conn,
        f"""SELECT u.id, u.email, u.name, u.role, u.activated_at, t.expires_at
            FROM tokens t JOIN users u ON t.user_id = u.id
            WHERE t.token = {p} AND u.banned = 0""",
        (token,))
    if not row:
        _close(conn)
        return None

    if row["role"] != "admin" and _is_account_expired(row["activated_at"]):
        _exec(conn, f"DELETE FROM tokens WHERE token = {p}", (token,))
        _commit(conn)
        _close(conn)
        return None

    expires = row["expires_at"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires < datetime.utcnow():
        _exec(conn, f"DELETE FROM tokens WHERE token = {p}", (token,))
        _commit(conn)
        _close(conn)
        return None

    _close(conn)
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "_token": token,
    }


def logout_token(token: str):
    conn = _get_db()
    p = _P()
    _exec(conn, f"DELETE FROM tokens WHERE token = {p}", (token,))
    _commit(conn)
    _close(conn)


def get_user_conversation_dir(user_id: int) -> Path:
    base = Path(__file__).parent.parent / "data" / "conversations" / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def generate_activation_code(note: str = "") -> dict:
    code = secrets.token_hex(8).upper()
    conn = _get_db()
    p = _P()
    _exec(conn, f"INSERT INTO activation_codes (code, note) VALUES ({p}, {p})", (code, note.strip()))
    _commit(conn)
    _close(conn)
    return {"success": True, "code": code}


def list_activation_codes() -> list[dict]:
    conn = _get_db()
    rows = _fetchall(conn, "SELECT id, code, note, used, created_at, used_at FROM activation_codes ORDER BY id DESC")
    _close(conn)
    return rows


def list_users() -> list[dict]:
    conn = _get_db()
    rows = _fetchall(conn, "SELECT id, email, name, role, created_at, activated_at, banned FROM users ORDER BY id")
    _close(conn)
    for d in rows:
        d["expired"] = False if d["role"] == "admin" else _is_account_expired(d.get("activated_at"))
    return rows


def toggle_ban_user(user_id: int) -> dict:
    conn = _get_db()
    p = _P()
    user = _fetchone(conn, f"SELECT id, banned FROM users WHERE id = {p}", (user_id,))
    if not user:
        _close(conn)
        return {"success": False, "error": "User not found."}
    new_val = 0 if user["banned"] else 1
    _exec(conn, f"UPDATE users SET banned = {p} WHERE id = {p}", (new_val, user_id))
    _commit(conn)
    _close(conn)
    return {"success": True, "banned": bool(new_val)}


def delete_user(user_id: int) -> dict:
    conn = _get_db()
    p = _P()
    user = _fetchone(conn, f"SELECT id, role FROM users WHERE id = {p}", (user_id,))
    if not user:
        _close(conn)
        return {"success": False, "error": "User not found."}
    if user["role"] == "admin":
        _close(conn)
        return {"success": False, "error": "Cannot delete admin account."}
    _exec(conn, f"DELETE FROM tokens WHERE user_id = {p}", (user_id,))
    _exec(conn, f"DELETE FROM users WHERE id = {p}", (user_id,))
    _commit(conn)
    _close(conn)
    import shutil
    user_dir = get_user_conversation_dir(user_id)
    if user_dir.exists():
        shutil.rmtree(str(user_dir))
    return {"success": True, "message": "User deleted."}


def reactivate_user(user_id: int) -> dict:
    conn = _get_db()
    p = _P()
    user = _fetchone(conn, f"SELECT id FROM users WHERE id = {p}", (user_id,))
    if not user:
        _close(conn)
        return {"success": False, "error": "User not found."}
    _exec(conn, f"UPDATE users SET activated_at = {_NOW()} WHERE id = {p}", (user_id,))
    _commit(conn)
    _close(conn)
    return {"success": True, "message": f"Account reactivated for another {ACCOUNT_EXPIRY_DAYS} days."}
