"""SQLite database models for users, conversations, messages, and audit logs."""
import sqlite3
import os
import uuid
from datetime import datetime
import bcrypt

from backend.config import Config


def get_db_connection():
    """Get a database connection."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables and default users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'support',
            department TEXT DEFAULT 'General',
            email TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    """)
    
    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT DEFAULT 'New Conversation',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT DEFAULT '[]',
            category TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    
    # Audit logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            query TEXT DEFAULT '',
            response_summary TEXT DEFAULT '',
            category TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0,
            sources TEXT DEFAULT '[]',
            ip_address TEXT DEFAULT '',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # Create default users if they don't exist
    default_users = [
        {
            "username": "admin",
            "password": "admin123",
            "full_name": "System Administrator",
            "role": "admin",
            "department": "IT Administration",
            "email": "admin@bank.com"
        },
        {
            "username": "ops_user",
            "password": "ops123",
            "full_name": "Operations Manager",
            "role": "operations",
            "department": "Banking Operations",
            "email": "ops@bank.com"
        },
        {
            "username": "compliance",
            "password": "comp123",
            "full_name": "Compliance Officer",
            "role": "compliance",
            "department": "Risk & Compliance",
            "email": "compliance@bank.com"
        },
        {
            "username": "support",
            "password": "support123",
            "full_name": "Support Agent",
            "role": "support",
            "department": "Customer Support",
            "email": "support@bank.com"
        },
    ]
    
    for user in default_users:
        try:
            pw_hash = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute(
                """INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role, department, email)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), user["username"], pw_hash, user["full_name"],
                 user["role"], user["department"], user["email"])
            )
        except Exception:
            pass
    
    conn.commit()
    conn.close()


class UserModel:
    """User database operations."""
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate a user and return user dict or None."""
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)).fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            # Update last login
            conn = get_db_connection()
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), user["id"]))
            conn.commit()
            conn.close()
            return dict(user)
        return None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None
    
    @staticmethod
    def get_all():
        """Get all users (admin only)."""
        conn = get_db_connection()
        users = conn.execute("SELECT id, username, full_name, role, department, email, is_active, created_at, last_login FROM users").fetchall()
        conn.close()
        return [dict(u) for u in users]
    
    @staticmethod
    def create(username, password, full_name, role, department, email=""):
        """Create a new user."""
        user_id = str(uuid.uuid4())
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn = get_db_connection()
        try:
            conn.execute(
                """INSERT INTO users (id, username, password_hash, full_name, role, department, email)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, pw_hash, full_name, role, department, email)
            )
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()


class ConversationModel:
    """Conversation database operations."""
    
    @staticmethod
    def create(user_id, title="New Conversation"):
        """Create a new conversation."""
        conv_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
            (conv_id, user_id, title)
        )
        conn.commit()
        conn.close()
        return conv_id
    
    @staticmethod
    def get_by_user(user_id, limit=50):
        """Get conversations for a user."""
        conn = get_db_connection()
        convs = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
        return [dict(c) for c in convs]
    
    @staticmethod
    def update_title(conv_id, title):
        """Update conversation title."""
        conn = get_db_connection()
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.utcnow().isoformat(), conv_id)
        )
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(conv_id):
        """Delete a conversation and its messages."""
        conn = get_db_connection()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        conn.close()


class MessageModel:
    """Message database operations."""
    
    @staticmethod
    def add(conversation_id, role, content, sources="[]", category="", confidence=0.0):
        """Add a message to a conversation."""
        msg_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO messages (id, conversation_id, role, content, sources, category, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, content, sources, category, confidence)
        )
        # Also update conversation timestamp
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), conversation_id)
        )
        conn.commit()
        conn.close()
        return msg_id
    
    @staticmethod
    def get_by_conversation(conversation_id, limit=100):
        """Get messages for a conversation."""
        conn = get_db_connection()
        msgs = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC LIMIT ?",
            (conversation_id, limit)
        ).fetchall()
        conn.close()
        return [dict(m) for m in msgs]
    
    @staticmethod
    def get_recent_context(conversation_id, limit=6):
        """Get recent messages for context window."""
        conn = get_db_connection()
        msgs = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit)
        ).fetchall()
        conn.close()
        return list(reversed([dict(m) for m in msgs]))


class AuditModel:
    """Audit log database operations."""
    
    @staticmethod
    def log(user_id, username, action, query="", response_summary="", category="", confidence=0.0, sources="[]", ip_address=""):
        """Log an audit event."""
        log_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO audit_logs (id, user_id, username, action, query, response_summary, category, confidence, sources, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, username, action, query, response_summary[:500], category, confidence, sources, ip_address)
        )
        conn.commit()
        conn.close()
        return log_id
    
    @staticmethod
    def get_logs(limit=200, user_id=None, action=None):
        """Get audit logs with optional filters."""
        conn = get_db_connection()
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        logs = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(l) for l in logs]
