"""SQLite Database service for Nyayavarta User Authentication and Chat History.

Provides secure credential storage (PBKDF2-HMAC-SHA256 with per-user salt),
session tokens, and strict per-user chat thread/message isolation.
"""

import sqlite3
import hashlib
import secrets
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "nyayavarta_auth.db"
)


class AuthDatabase:
    """Manages SQLite storage for authentication and private chat consultations."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

            # 2. Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")

            # 3. Chat Threads table (isolated per user)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_threads_user_id ON chat_threads(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_threads_updated ON chat_threads(updated_at DESC)")

            # 4. Chat Messages table (isolated per thread & user)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    original_query TEXT,
                    english_query TEXT,
                    regional_response TEXT,
                    english_response TEXT,
                    citations_json TEXT,
                    audio_base64 TEXT,
                    detected_language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_user ON chat_messages(thread_id, user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON chat_messages(created_at ASC)")
            conn.commit()
            logger.info(f"Auth & Chat database initialized at {self.db_path}")

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password using PBKDF2-HMAC-SHA256 with 100,000 rounds."""
        if not salt:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()
        return pwd_hash, salt

    @staticmethod
    def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
        """Verify password in constant time."""
        pwd_hash, _ = AuthDatabase._hash_password(password, salt)
        return secrets.compare_digest(pwd_hash, expected_hash)

    # -------------------------------------------------------------
    # User Authentication Methods
    # -------------------------------------------------------------
    def register_user(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Register a new user with hashed credentials."""
        clean_email = email.strip().lower()
        clean_name = full_name.strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("A valid email address is required.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        if not clean_name:
            raise ValueError("Full name is required.")

        user_id = f"usr_{secrets.token_hex(12)}"
        pwd_hash, salt = self._hash_password(password)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check existing email
            cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
            if cursor.fetchone():
                raise ValueError("An account with this email already exists.")

            cursor.execute("""
                INSERT INTO users (id, email, password_hash, salt, full_name)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, clean_email, pwd_hash, salt, clean_name))
            conn.commit()

        # Create session token upon registration
        token = self.create_session(user_id)
        return {
            "token": token,
            "user": {
                "id": user_id,
                "email": clean_email,
                "full_name": clean_name
            }
        }

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate an existing user and create a session token."""
        clean_email = email.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, password_hash, salt, full_name FROM users WHERE email = ?", (clean_email,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Invalid email or password.")

            if not self._verify_password(password, row["salt"], row["password_hash"]):
                raise ValueError("Invalid email or password.")

            user_id = row["id"]
            user_data = {
                "id": user_id,
                "email": row["email"],
                "full_name": row["full_name"]
            }

        token = self.create_session(user_id)
        return {
            "token": token,
            "user": user_data
        }

    def create_session(self, user_id: str, days_valid: int = 30) -> str:
        """Create a secure 32-byte hex session token valid for days_valid."""
        token = secrets.token_hex(32)
        expires_at = datetime.utcnow() + timedelta(days=days_valid)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (token, user_id, expires_at)
                VALUES (?, ?, ?)
            """, (token, user_id, expires_at.isoformat()))
            conn.commit()
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token and return user data if valid and unexpired."""
        if not token:
            return None
        now_str = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.token, s.expires_at, u.id, u.email, u.full_name
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > ?
            """, (token, now_str))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"]
            }

    def delete_session(self, token: str) -> bool:
        """Delete a session (logout)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # Isolated Chat History & Thread Methods
    # -------------------------------------------------------------
    def create_thread(self, user_id: str, title: Optional[str] = None, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new consultation thread for a user."""
        t_id = thread_id or f"th_{secrets.token_hex(10)}"
        clean_title = (title or "New Legal Consultation").strip()[:80]
        now_str = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_threads (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (t_id, user_id, clean_title, now_str, now_str))
            conn.commit()

        return {
            "id": t_id,
            "user_id": user_id,
            "title": clean_title,
            "created_at": now_str,
            "updated_at": now_str,
            "message_count": 0
        }

    def get_user_threads(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all consultation threads for the specific user (strictly isolated)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.title, t.created_at, t.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_threads t
                LEFT JOIN chat_messages m ON t.id = m.thread_id
                WHERE t.user_id = ?
                GROUP BY t.id
                ORDER BY t.updated_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"]
                }
                for row in rows
            ]

    def get_thread(self, user_id: str, thread_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve thread metadata if owned by user_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, title, created_at, updated_at
                FROM chat_threads
                WHERE id = ? AND user_id = ?
            """, (thread_id, user_id))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def update_thread_title(self, user_id: str, thread_id: str, title: str) -> bool:
        """Update thread title if owned by user_id."""
        clean_title = title.strip()[:80]
        now_str = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE chat_threads
                SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (clean_title, now_str, thread_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_thread(self, user_id: str, thread_id: str) -> bool:
        """Delete thread and its messages if owned by user_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_threads WHERE id = ? AND user_id = ?", (thread_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_message(
        self,
        user_id: str,
        thread_id: str,
        sender: str,
        original_query: Optional[str] = None,
        english_query: Optional[str] = None,
        regional_response: Optional[str] = None,
        english_response: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        audio_base64: Optional[str] = None,
        detected_language: Optional[str] = "hi",
        msg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a thread owned by user_id."""
        # Ensure thread exists and belongs to user
        thread = self.get_thread(user_id, thread_id)
        if not thread:
            # Auto-create thread if it doesn't exist
            initial_title = (original_query or "Legal Consultation")[:50]
            self.create_thread(user_id, title=initial_title, thread_id=thread_id)

        m_id = msg_id or f"msg_{secrets.token_hex(10)}"
        now_str = datetime.utcnow().isoformat()
        citations_json = json.dumps(citations or [])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (
                    id, thread_id, user_id, sender, original_query, english_query,
                    regional_response, english_response, citations_json, audio_base64,
                    detected_language, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m_id, thread_id, user_id, sender, original_query, english_query,
                regional_response, english_response, citations_json, audio_base64,
                detected_language, now_str
            ))
            # Touch thread updated_at
            cursor.execute("UPDATE chat_threads SET updated_at = ? WHERE id = ?", (now_str, thread_id))
            conn.commit()

        return {
            "id": m_id,
            "thread_id": thread_id,
            "sender": sender,
            "original_query": original_query,
            "english_query": english_query,
            "regional_response": regional_response,
            "english_response": english_response,
            "citations": citations or [],
            "audio_base64": audio_base64,
            "detected_language": detected_language,
            "created_at": now_str
        }

    def get_thread_messages(self, user_id: str, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages for a thread owned by user_id."""
        # Strict isolation check
        thread = self.get_thread(user_id, thread_id)
        if not thread:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, thread_id, user_id, sender, original_query, english_query,
                       regional_response, english_response, citations_json, audio_base64,
                       detected_language, created_at
                FROM chat_messages
                WHERE thread_id = ? AND user_id = ?
                ORDER BY created_at ASC
            """, (thread_id, user_id))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                citations = []
                if row["citations_json"]:
                    try:
                        citations = json.loads(row["citations_json"])
                    except Exception:
                        citations = []
                messages.append({
                    "id": row["id"],
                    "thread_id": row["thread_id"],
                    "sender": row["sender"],
                    "original_query": row["original_query"],
                    "english_query": row["english_query"],
                    "regional_response": row["regional_response"],
                    "english_response": row["english_response"],
                    "citations": citations,
                    "audio_base64": row["audio_base64"],
                    "detected_language": row["detected_language"],
                    "created_at": row["created_at"]
                })
            return messages


# Global singleton instance
_auth_db_instance: Optional[AuthDatabase] = None


def get_auth_db() -> AuthDatabase:
    """Get or initialize singleton instance of AuthDatabase."""
    global _auth_db_instance
    if _auth_db_instance is None:
        _auth_db_instance = AuthDatabase()
    return _auth_db_instance
