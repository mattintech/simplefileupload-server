import sqlite3
import secrets
from datetime import datetime
from models.database import get_db
import utils.mLogger as log


def generate_client_key():
    """Generate a random 64-character hex string (256 bits)"""
    return secrets.token_hex(32)  # 32 bytes = 64 hex chars


def generate_secret_key():
    """Generate a random 64-character hex string for Flask SECRET_KEY"""
    return secrets.token_hex(32)  # 32 bytes = 64 hex chars


def get_config():
    """Get server configuration (singleton)

    Returns:
        dict: Configuration with client_key, secret_key, server_address, server_port, timestamps
        None: If config doesn't exist or error occurred
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT client_key, secret_key, server_address, server_port, created_at, updated_at
                FROM server_config
                WHERE id = 1
            """).fetchone()

            if row:
                return dict(row)
            return None
    except sqlite3.Error as e:
        log.e(f"Error getting config: {e}")
        return None


def get_client_key():
    """Get only the client key for authentication

    Returns:
        str: The client key
        None: If config doesn't exist or error occurred
    """
    config = get_config()
    return config['client_key'] if config else None


def get_secret_key():
    """Get the Flask secret key from database

    Returns:
        str: The secret key
        None: If config doesn't exist or error occurred
    """
    config = get_config()
    return config['secret_key'] if config else None


def init_config(client_key=None, secret_key=None):
    """Initialize server config with provided or generated keys

    Args:
        client_key (str, optional): Client key to use. If None, generates new key
        secret_key (str, optional): Secret key to use. If None, generates new key

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            # Check if config already exists
            existing = conn.execute("SELECT COUNT(*) FROM server_config WHERE id = 1").fetchone()[0]

            if existing > 0:
                log.i("Server config already exists, skipping initialization")
                return True

            # Generate keys if not provided
            if not client_key:
                client_key = generate_client_key()
                log.i("Generated new client key")
            else:
                log.i("Using provided client key from environment")

            if not secret_key:
                secret_key = generate_secret_key()
                log.i("Generated new secret key")
            else:
                log.i("Using provided secret key from environment")

            # Insert initial config
            now = datetime.now().isoformat()

            conn.execute("""
                INSERT INTO server_config (id, client_key, secret_key, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?)
            """, (client_key, secret_key, now, now))

            log.i("Server config initialized successfully")
            return True
    except sqlite3.Error as e:
        log.e(f"Error initializing config: {e}")
        return False


def update_server_address(address):
    """Update server address

    Args:
        address (str): Server address (IP or hostname)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            conn.execute("""
                UPDATE server_config
                SET server_address = ?, updated_at = ?
                WHERE id = 1
            """, (address, datetime.now().isoformat()))

            log.i(f"Updated server address: {address}")
            return True
    except sqlite3.Error as e:
        log.e(f"Error updating server address: {e}")
        return False


def update_server_port(port):
    """Update server port

    Args:
        port (int): Server port number

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            conn.execute("""
                UPDATE server_config
                SET server_port = ?, updated_at = ?
                WHERE id = 1
            """, (port, datetime.now().isoformat()))

            log.i(f"Updated server port: {port}")
            return True
    except sqlite3.Error as e:
        log.e(f"Error updating server port: {e}")
        return False


def regenerate_client_key():
    """Generate and set a new client key

    Returns:
        str: The new client key
        None: If error occurred
    """
    try:
        new_key = generate_client_key()

        with get_db() as conn:
            conn.execute("""
                UPDATE server_config
                SET client_key = ?, updated_at = ?
                WHERE id = 1
            """, (new_key, datetime.now().isoformat()))

            log.w("Client key regenerated - all clients must update!")
            return new_key
    except sqlite3.Error as e:
        log.e(f"Error regenerating client key: {e}")
        return None
