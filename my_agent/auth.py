import sqlite3
import hashlib
import secrets
import json
import time
import os
import smtplib
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.text import MIMEText


DB_PATH = Path(__file__).parent.parent / "data" / "bart.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TOKEN_EXPIRY_DAYS = 30

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

_verification_codes: dict[str, dict] = {}


def _send_email(to: str, subject: str, body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = to
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:
        return False


def send_verification_code(email: str, password: str, name: str = "") -> dict:
    email = email.lower().strip()
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    conn = _get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if existing:
        return {"success": False, "error": "Email already registered."}

    code = f"{secrets.randbelow(900000) + 100000}"
    _verification_codes[email] = {
        "code": code,
        "password": password,
        "name": name.strip(),
        "expires": time.time() + 600,
    }
    sent = _send_email(email, "Your BArt AI Verification Code", f"Your verification code is: {code}\n\nThis code expires in 10 minutes.")
    if not sent:
        return {"success": False, "error": "Failed to send verification email. Check SMTP settings."}
    return {"success": True, "message": "Verification code sent to your email."}


def verify_email(email: str, code: str) -> dict:
    email = email.lower().strip()
    data = _verification_codes.pop(email, None)
    if not data:
        return {"success": False, "error": "No verification code found. Please register again."}
    if time.time() > data["expires"]:
        return {"success": False, "error": "Verification code expired. Please register again."}
    if data["code"] != code.strip():
        _verification_codes[email] = data
        return {"success": False, "error": "Invalid verification code."}

    pw = _hash_password(data["password"])
    conn = _get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email, pw, data["name"]),
        )
        conn.commit()
        return {"success": True, "message": "Email verified and account created!"}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()


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


def register_user(email: str, password: str, name: str = "") -> dict:
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    conn = _get_db()
    try:
        pw = _hash_password(password)
        conn.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email.lower().strip(), pw, name.strip()),
        )
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()


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


def list_users() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, email, name, role, created_at, banned FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
