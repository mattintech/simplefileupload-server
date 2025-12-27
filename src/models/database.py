import sqlite3
import json
import os
from contextlib import contextmanager
import utils.mLogger as log

# Database file location (relative to server directory)
DB_DIR = 'db'
DB_PATH = os.path.join(DB_DIR, 'file_server.db')

# Ensure database directory exists
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def get_db_connection():
    """Get a thread-safe database connection with row factory"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Access columns by name

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")

    # Set busy timeout to 5 seconds to handle concurrent access
    conn.execute("PRAGMA busy_timeout=5000")

    return conn

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.e(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database with schema"""
    log.i("Initializing database...")

    with get_db() as conn:
        # Admin table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                totp_secret TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_admin_username ON admin(username)
        """)

        # Files table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                max_downloads INTEGER NOT NULL DEFAULT 1,
                downloads INTEGER NOT NULL DEFAULT 0,
                expiry_time TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                CONSTRAINT code_length CHECK(length(code) = 6),
                CONSTRAINT max_downloads_positive CHECK(max_downloads > 0),
                CONSTRAINT downloads_non_negative CHECK(downloads >= 0)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_code ON files(code)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_expiry ON files(expiry_time)
        """)

        # Chunk sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunk_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                total_chunks INTEGER NOT NULL,
                received_chunks TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                chunk_dir TEXT NOT NULL,
                max_downloads INTEGER NOT NULL DEFAULT 1,
                expiry_hours INTEGER NOT NULL DEFAULT 24,
                CONSTRAINT upload_id_length CHECK(length(upload_id) = 16),
                CONSTRAINT total_chunks_positive CHECK(total_chunks > 0)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_sessions_upload_id ON chunk_sessions(upload_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_sessions_created_at ON chunk_sessions(created_at)
        """)

        # Server configuration table (singleton)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                client_key TEXT NOT NULL,
                server_address TEXT,
                server_port INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CONSTRAINT client_key_length CHECK(length(client_key) = 64)
            )
        """)

    log.i("Database initialized successfully")

def migrate_from_json():
    """One-time migration from JSON files to SQLite"""

    # Check if we need to migrate
    admin_json = 'admin_data.json'
    file_json = 'file_metadata.json'
    chunk_json = 'chunk_metadata.json'

    # Only migrate if at least one JSON file exists
    if not any(os.path.exists(f) for f in [admin_json, file_json, chunk_json]):
        log.i("No JSON files found, skipping migration")
        return

    log.i("Starting migration from JSON to SQLite...")
    migrated = False

    with get_db() as conn:
        # Migrate admin_data.json
        if os.path.exists(admin_json):
            try:
                with open(admin_json, 'r') as f:
                    admin = json.load(f)

                # Check if admin already exists in database
                existing = conn.execute("SELECT COUNT(*) FROM admin").fetchone()[0]

                if existing == 0:
                    conn.execute("""
                        INSERT INTO admin (username, password_hash, totp_secret, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (admin['username'], admin['password_hash'],
                          admin['totp_secret'], admin['created_at']))
                    log.i(f"Migrated admin user: {admin['username']}")
                    migrated = True
                else:
                    log.i("Admin already exists in database, skipping admin migration")
            except Exception as e:
                log.e(f"Error migrating admin_data.json: {e}")

        # Migrate file_metadata.json
        if os.path.exists(file_json):
            try:
                with open(file_json, 'r') as f:
                    files = json.load(f)

                file_count = 0
                for code, file_info in files.items():
                    # Check if file already exists
                    existing = conn.execute("SELECT COUNT(*) FROM files WHERE code = ?", (code,)).fetchone()[0]

                    if existing == 0:
                        conn.execute("""
                            INSERT INTO files (code, filename, path, max_downloads, downloads, expiry_time)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (code, file_info['filename'], file_info['path'],
                              file_info['max_downloads'], file_info['downloads'],
                              file_info['expiry_time']))
                        file_count += 1

                if file_count > 0:
                    log.i(f"Migrated {file_count} file(s)")
                    migrated = True
                else:
                    log.i("No new files to migrate")
            except Exception as e:
                log.e(f"Error migrating file_metadata.json: {e}")

        # Migrate chunk_metadata.json
        if os.path.exists(chunk_json):
            try:
                with open(chunk_json, 'r') as f:
                    chunks = json.load(f)

                chunk_count = 0
                for upload_id, session in chunks.items():
                    # Check if session already exists
                    existing = conn.execute("SELECT COUNT(*) FROM chunk_sessions WHERE upload_id = ?", (upload_id,)).fetchone()[0]

                    if existing == 0:
                        conn.execute("""
                            INSERT INTO chunk_sessions
                            (upload_id, filename, total_chunks, received_chunks, created_at,
                             chunk_dir, max_downloads, expiry_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (upload_id, session['filename'], session['total_chunks'],
                              json.dumps(session['received_chunks']), session['created_at'],
                              session['chunk_dir'], session['max_downloads'],
                              session['expiry_hours']))
                        chunk_count += 1

                if chunk_count > 0:
                    log.i(f"Migrated {chunk_count} chunk session(s)")
                    migrated = True
                else:
                    log.i("No new chunk sessions to migrate")
            except Exception as e:
                log.e(f"Error migrating chunk_metadata.json: {e}")

    # Backup JSON files after successful migration
    if migrated:
        for filename in [admin_json, file_json, chunk_json]:
            if os.path.exists(filename):
                backup_name = f'{filename}.backup'
                try:
                    os.rename(filename, backup_name)
                    log.i(f"Backed up {filename} to {backup_name}")
                except Exception as e:
                    log.w(f"Could not backup {filename}: {e}")

        log.i("Migration completed successfully")
    else:
        log.i("No migration performed")


def migrate_client_key_to_db():
    """Migrate CLIENT_KEY from environment to database (one-time)"""
    from models.config_model import init_config

    # Only run if config doesn't exist
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM server_config WHERE id = 1").fetchone()[0]

        if existing > 0:
            log.i("Server config already exists in database, skipping migration")
            return

    # Get CLIENT_KEY from environment if set
    env_key = os.environ.get('CLIENT_KEY')

    # Initialize config (will generate new key if env_key is None or default)
    if env_key and env_key != 'default-secret-key':
        log.i("Migrating CLIENT_KEY from environment to database")
        init_config(client_key=env_key)
    else:
        log.i("No valid CLIENT_KEY in environment, generating new key")
        init_config()
