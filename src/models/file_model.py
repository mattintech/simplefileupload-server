import sqlite3
import os
from datetime import datetime, timedelta
from models.database import get_db
import utils.mLogger as log

def create_file(code, filename, path, max_downloads, expiry_hours):
    """Create a new file metadata record

    Args:
        code: 6-character unique code
        filename: Original filename
        path: Absolute path to file
        max_downloads: Maximum number of downloads allowed
        expiry_hours: Hours until file expires

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            expiry_time = datetime.now() + timedelta(hours=expiry_hours)

            conn.execute("""
                INSERT INTO files (code, filename, path, max_downloads, downloads, expiry_time)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (code, filename, path, max_downloads, expiry_time.isoformat()))

            log.i(f"Created file record: {code} - {filename}")
            return True
    except sqlite3.Error as e:
        log.e(f"Error creating file record: {e}")
        return False

def get_file(code):
    """Get file metadata by code

    Args:
        code: 6-character file code

    Returns:
        dict: File metadata with keys: code, filename, path, max_downloads, downloads, expiry_time
        None: If file not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT code, filename, path, max_downloads, downloads, expiry_time
                FROM files
                WHERE code = ?
            """, (code,)).fetchone()

            if row:
                return dict(row)
            return None
    except sqlite3.Error as e:
        log.e(f"Error getting file {code}: {e}")
        return None

def increment_download(code):
    """Atomically increment download counter for a file

    Args:
        code: 6-character file code

    Returns:
        int: New download count, or None if file not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE files
                SET downloads = downloads + 1
                WHERE code = ?
            """, (code,))

            if cursor.rowcount > 0:
                # Get the new download count
                row = cursor.execute("""
                    SELECT downloads FROM files WHERE code = ?
                """, (code,)).fetchone()

                if row:
                    new_count = row['downloads']
                    log.i(f"Incremented download counter for {code}: {new_count}")
                    return new_count

            return None
    except sqlite3.Error as e:
        log.e(f"Error incrementing download for {code}: {e}")
        return None

def delete_file(code):
    """Delete file metadata record

    Args:
        code: 6-character file code

    Returns:
        bool: True if deleted, False if not found or error
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE code = ?", (code,))

            if cursor.rowcount > 0:
                log.i(f"Deleted file record: {code}")
                return True
            return False
    except sqlite3.Error as e:
        log.e(f"Error deleting file {code}: {e}")
        return False

def get_expired_files():
    """Get list of expired files or files that exceeded download limit

    Returns:
        list: List of dicts with file metadata
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            rows = cursor.execute("""
                SELECT code, filename, path, max_downloads, downloads, expiry_time
                FROM files
                WHERE expiry_time < ? OR downloads >= max_downloads
            """, (now,)).fetchall()

            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        log.e(f"Error getting expired files: {e}")
        return []

def cleanup_expired():
    """Delete expired file records and files that reached download limit

    Returns:
        int: Number of files cleaned up
    """
    try:
        # Get expired files first so we can delete physical files
        expired_files = get_expired_files()

        if not expired_files:
            return 0

        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Delete from database
            cursor.execute("""
                DELETE FROM files
                WHERE expiry_time < ? OR downloads >= max_downloads
            """, (now,))

            count = cursor.rowcount

            # Delete physical files
            for file_info in expired_files:
                if os.path.exists(file_info['path']):
                    try:
                        os.remove(file_info['path'])
                        log.i(f"Deleted expired file: {file_info['path']}")
                    except Exception as e:
                        log.w(f"Could not delete file {file_info['path']}: {e}")

            if count > 0:
                log.i(f"Cleaned up {count} expired file(s)")

            return count
    except sqlite3.Error as e:
        log.e(f"Error cleaning up expired files: {e}")
        return 0

def get_all_files():
    """Get all file metadata records

    Returns:
        list: List of dicts with file metadata
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT code, filename, path, max_downloads, downloads, expiry_time, created_at
                FROM files
                ORDER BY created_at DESC
            """).fetchall()

            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        log.e(f"Error getting all files: {e}")
        return []
