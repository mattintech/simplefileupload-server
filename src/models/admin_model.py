import sqlite3
from models.database import get_db
import utils.mLogger as log

def get_admin():
    """Get admin user data

    Returns:
        dict: Admin data with keys: username, password_hash, totp_secret, created_at, last_login
        None: If no admin exists
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT username, password_hash, totp_secret, created_at, last_login
                FROM admin
                LIMIT 1
            """).fetchone()

            if row:
                return dict(row)
            return None
    except sqlite3.Error as e:
        log.e(f"Error getting admin data: {e}")
        return None

def create_admin(username, password_hash, totp_secret):
    """Create admin user

    Args:
        username: Admin username
        password_hash: Hashed password
        totp_secret: TOTP secret for 2FA

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            from datetime import datetime

            conn.execute("""
                INSERT INTO admin (username, password_hash, totp_secret, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, totp_secret, datetime.now().isoformat()))

            log.i(f"Admin user created: {username}")
            return True
    except sqlite3.Error as e:
        log.e(f"Error creating admin: {e}")
        return False

def admin_exists():
    """Check if an admin user has been created

    Returns:
        bool: True if admin exists, False otherwise
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            count = cursor.execute("SELECT COUNT(*) FROM admin").fetchone()[0]
            return count > 0
    except sqlite3.Error as e:
        log.e(f"Error checking if admin exists: {e}")
        return False

def update_last_login(username):
    """Update admin's last login time

    Args:
        username: Admin username

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            from datetime import datetime

            conn.execute("""
                UPDATE admin
                SET last_login = ?
                WHERE username = ?
            """, (datetime.now().isoformat(), username))

            return True
    except sqlite3.Error as e:
        log.e(f"Error updating last login: {e}")
        return False
