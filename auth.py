"""
Simple multi-user authentication for the Streamlit app.

Users are stored in data/users.json with salted PBKDF2 password hashes
(never plain-text passwords). Each user gets their own progress file:
data/users/<username>_progress.json
"""

import hashlib
import hmac
import json
import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
USER_DATA_DIR = os.path.join(BASE_DIR, "users")

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
_ITERATIONS = 200_000


def _load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_users(users: dict):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS).hex()


def normalize_username(username: str) -> str:
    return username.strip().lower()


PASSWORD_LENGTH = 5
PASSWORD_HINT = "Password: exactly 5 characters (letters, numbers or symbols)."


def validate_password(password: str) -> tuple[bool, str]:
    """Password rule (applied at sign-up only, so existing accounts keep working)."""
    if len(password) != PASSWORD_LENGTH:
        return False, f"Password must be exactly {PASSWORD_LENGTH} characters."
    if " " in password:
        return False, "Password cannot contain spaces."
    return True, ""


def register(username: str, password: str) -> tuple[bool, str]:
    """Create a new account. Returns (ok, message)."""
    username = normalize_username(username)
    if not _USERNAME_RE.match(username):
        return False, "Username must be 3-20 characters: letters, numbers or underscore."
    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    users = _load_users()
    if username in users:
        return False, "That username is already taken."

    salt = os.urandom(16)
    users[username] = {"salt": salt.hex(), "hash": _hash(password, salt)}
    _save_users(users)
    return True, "Account created."


def authenticate(username: str, password: str) -> bool:
    username = normalize_username(username)
    user = _load_users().get(username)
    if not user:
        return False
    expected = _hash(password, bytes.fromhex(user["salt"]))
    return hmac.compare_digest(expected, user["hash"])


def progress_file_for(username: str) -> str:
    """Path of the per-user progress file."""
    return os.path.join(USER_DATA_DIR, f"{normalize_username(username)}_progress.json")
