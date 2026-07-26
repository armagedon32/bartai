import sqlite3
import hashlib
import secrets
import json
import time
from pathlib import Path
from datetime import datetime, timedelta


DB_PATH = Path(__file__).parent.parent / "data" / "bart.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TOKEN_EXPIRY_DAYS = 30


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


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
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            banned INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS activation_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            used_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def seed_admin():
    conn = _get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", ("admin@bart.ai",)).fetchone()
    if not existing:
        pw = _hash_password("admin123")
        conn.execute(
            "INSERT INTO users (email, password, name, role) VALUES (?, ?, ?, ?)",
            ("admin@bart.ai", pw, "Admin", "admin"),
        )
        conn.commit()
        print("Default admin account: admin@bart.ai / admin123")
    conn.close()


def register_with_code(email: str, password: str, code: str, name: str = "") -> dict:
    email = email.lower().strip()
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not code:
        return {"success": False, "error": "Activation code is required."}

    conn = _get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return {"success": False, "error": "Email already registered."}

    row = conn.execute(
        "SELECT id, used FROM activation_codes WHERE code = ?", (code.strip(),)
    ).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Invalid activation code."}
    if row["used"]:
        conn.close()
        return {"success": False, "error": "Activation code already used."}

    pw = _hash_password(password)
    conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, pw, name.strip()))
    conn.execute("UPDATE activation_codes SET used = 1, used_at = datetime('now') WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Account created successfully!"}


def login_user(email: str, password: str) -> dict:
    conn = _get_db()
    user = conn.execute(
        "SELECT id, email, password, name, role, banned FROM users WHERE email = ?",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()

    if not user:
        return {"success": False, "error": "Invalid email or password."}
    if user["banned"]:
        return {"success": False, "error": "Account is disabled."}
    if not _verify_password(password, user["password"]):
        return {"success": False, "error": "Invalid email or password."}

    token = secrets.token_hex(32)
    expires = (datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS)).isoformat()

    conn = _get_db()
    conn.execute(
        "INSERT INTO tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user["id"], token, expires),
    )
    conn.commit()
    conn.close()

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
    row = conn.execute(
        """SELECT u.id, u.email, u.name, u.role, t.expires_at
           FROM tokens t JOIN users u ON t.user_id = u.id
           WHERE t.token = ? AND u.banned = 0""",
        (token,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    expires = datetime.fromisoformat(row["expires_at"])
    if expires < datetime.utcnow():
        conn = _get_db()
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "_token": token,
    }


def logout_token(token: str):
    conn = _get_db()
    conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def get_user_conversation_dir(user_id: int) -> Path:
    base = Path(__file__).parent.parent / "data" / "conversations" / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def generate_activation_code(note: str = "") -> dict:
    code = secrets.token_hex(8).upper()
    conn = _get_db()
    conn.execute(
        "INSERT INTO activation_codes (code, note) VALUES (?, ?)",
        (code, note.strip()),
    )
    conn.commit()
    conn.close()
    return {"success": True, "code": code}


def list_activation_codes() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, code, note, used, created_at, used_at FROM activation_codes ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_users() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, email, name, role, created_at, banned FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_ban_user(user_id: int) -> dict:
    conn = _get_db()
    user = conn.execute("SELECT id, banned FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return {"success": False, "error": "User not found."}
    new_val = 0 if user["banned"] else 1
    conn.execute("UPDATE users SET banned = ? WHERE id = ?", (new_val, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "banned": bool(new_val)}
