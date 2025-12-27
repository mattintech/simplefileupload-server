import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta
from models.database import get_db
import utils.mLogger as log

def create_session(upload_id, filename, total_chunks, chunk_dir, max_downloads, expiry_hours):
    """Create a new chunked upload session

    Args:
        upload_id: 16-character unique upload ID
        filename: Original filename
        total_chunks: Total number of chunks expected
        chunk_dir: Directory where chunks are stored
        max_downloads: Maximum downloads for final file
        expiry_hours: Expiry hours for final file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO chunk_sessions
                (upload_id, filename, total_chunks, received_chunks, created_at,
                 chunk_dir, max_downloads, expiry_hours)
                VALUES (?, ?, ?, '[]', ?, ?, ?, ?)
            """, (upload_id, filename, total_chunks, datetime.now().isoformat(),
                  chunk_dir, max_downloads, expiry_hours))

            log.i(f"Created chunk session: {upload_id}")
            return True
    except sqlite3.Error as e:
        log.e(f"Error creating chunk session: {e}")
        return False

def get_session(upload_id):
    """Get chunk upload session data

    Args:
        upload_id: 16-character upload ID

    Returns:
        dict: Session data with keys: upload_id, filename, total_chunks, received_chunks (list),
              created_at, chunk_dir, max_downloads, expiry_hours
        None: If session not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT upload_id, filename, total_chunks, received_chunks, created_at,
                       chunk_dir, max_downloads, expiry_hours
                FROM chunk_sessions
                WHERE upload_id = ?
            """, (upload_id,)).fetchone()

            if row:
                data = dict(row)
                # Parse received_chunks from JSON string to list
                data['received_chunks'] = json.loads(data['received_chunks'])
                return data
            return None
    except sqlite3.Error as e:
        log.e(f"Error getting chunk session {upload_id}: {e}")
        return None

def add_chunk(upload_id, chunk_index):
    """Add a chunk index to the received chunks list

    Args:
        upload_id: 16-character upload ID
        chunk_index: Index of the chunk received

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get current received_chunks
            row = cursor.execute("""
                SELECT received_chunks FROM chunk_sessions WHERE upload_id = ?
            """, (upload_id,)).fetchone()

            if not row:
                log.e(f"Chunk session not found: {upload_id}")
                return False

            received = json.loads(row['received_chunks'])

            # Add chunk index if not already present
            if chunk_index not in received:
                received.append(chunk_index)

                # Update database
                cursor.execute("""
                    UPDATE chunk_sessions
                    SET received_chunks = ?
                    WHERE upload_id = ?
                """, (json.dumps(received), upload_id))

                log.i(f"Added chunk {chunk_index} to session {upload_id}")
                return True
            else:
                log.w(f"Chunk {chunk_index} already in session {upload_id}")
                return True
    except sqlite3.Error as e:
        log.e(f"Error adding chunk to session {upload_id}: {e}")
        return False

def get_received_chunks(upload_id):
    """Get list of received chunk indices

    Args:
        upload_id: 16-character upload ID

    Returns:
        list: List of chunk indices, or None if session not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT received_chunks FROM chunk_sessions WHERE upload_id = ?
            """, (upload_id,)).fetchone()

            if row:
                return json.loads(row['received_chunks'])
            return None
    except sqlite3.Error as e:
        log.e(f"Error getting received chunks for {upload_id}: {e}")
        return None

def delete_session(upload_id):
    """Delete chunk upload session

    Args:
        upload_id: 16-character upload ID

    Returns:
        bool: True if deleted, False if not found or error
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunk_sessions WHERE upload_id = ?", (upload_id,))

            if cursor.rowcount > 0:
                log.i(f"Deleted chunk session: {upload_id}")
                return True
            return False
    except sqlite3.Error as e:
        log.e(f"Error deleting chunk session {upload_id}: {e}")
        return False

def get_abandoned_sessions(hours=24):
    """Get list of abandoned upload sessions older than specified hours

    Args:
        hours: Age threshold in hours (default: 24)

    Returns:
        list: List of dicts with session metadata
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            rows = cursor.execute("""
                SELECT upload_id, filename, total_chunks, received_chunks, created_at,
                       chunk_dir, max_downloads, expiry_hours
                FROM chunk_sessions
                WHERE created_at < ?
            """, (cutoff_time,)).fetchall()

            sessions = []
            for row in rows:
                data = dict(row)
                data['received_chunks'] = json.loads(data['received_chunks'])
                sessions.append(data)

            return sessions
    except sqlite3.Error as e:
        log.e(f"Error getting abandoned sessions: {e}")
        return []

def cleanup_abandoned(hours=24):
    """Delete abandoned upload sessions and their chunk directories

    Args:
        hours: Age threshold in hours (default: 24)

    Returns:
        int: Number of sessions cleaned up
    """
    try:
        # Get abandoned sessions first so we can clean up directories
        abandoned = get_abandoned_sessions(hours)

        if not abandoned:
            return 0

        with get_db() as conn:
            cursor = conn.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Delete from database
            cursor.execute("""
                DELETE FROM chunk_sessions
                WHERE created_at < ?
            """, (cutoff_time,))

            count = cursor.rowcount

            # Delete chunk directories
            for session in abandoned:
                if os.path.exists(session['chunk_dir']):
                    try:
                        shutil.rmtree(session['chunk_dir'])
                        log.i(f"Deleted chunk directory: {session['chunk_dir']}")
                    except Exception as e:
                        log.w(f"Could not delete chunk directory {session['chunk_dir']}: {e}")

            if count > 0:
                log.i(f"Cleaned up {count} abandoned upload session(s)")

            return count
    except sqlite3.Error as e:
        log.e(f"Error cleaning up abandoned sessions: {e}")
        return 0

def update_received_chunks(upload_id, received_chunks):
    """Update the entire received_chunks list (used for verification corrections)

    Args:
        upload_id: 16-character upload ID
        received_chunks: List of chunk indices

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE chunk_sessions
                SET received_chunks = ?
                WHERE upload_id = ?
            """, (json.dumps(received_chunks), upload_id))

            if cursor.rowcount > 0:
                log.i(f"Updated received_chunks for session {upload_id}")
                return True
            return False
    except sqlite3.Error as e:
        log.e(f"Error updating received_chunks for {upload_id}: {e}")
        return False
