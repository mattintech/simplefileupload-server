import os
import random
import string
import json
import shutil
from datetime import datetime, timedelta
from flask import request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
import utils.mLogger as log
from models.file_metadata import FileMetadata

# Make UPLOAD_FOLDER absolute
UPLOAD_FOLDER = os.path.abspath('tmp/uploads')
METADATA_FILE = 'file_metadata.json'

# Constants for chunked uploads
CHUNKS_FOLDER = os.path.join(UPLOAD_FOLDER, 'chunks')
CHUNK_METADATA_FILE = 'chunk_metadata.json'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ensure chunks directory exists
if not os.path.exists(CHUNKS_FOLDER):
    os.makedirs(CHUNKS_FOLDER)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

def load_chunk_metadata():
    if os.path.exists(CHUNK_METADATA_FILE):
        with open(CHUNK_METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_chunk_metadata(metadata):
    with open(CHUNK_METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_upload_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=16))

def upload_file():
    if 'file' not in request.files:
        log.e("No File Part")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        log.e("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    log.i(f"File upload: {file_path}")
    file.save(file_path)

    # Generate a unique 6-digit alphanumeric code
    code = generate_unique_code()

    # Get metadata from request
    max_downloads = int(request.form.get('max_downloads', 1))
    expiry_hours = int(request.form.get('expiry_hours', 24))
    expiry_time = datetime.now() + timedelta(hours=expiry_hours)

    # Save metadata
    metadata = load_metadata()
    metadata[code] = {
        'filename': filename,
        'path': file_path,
        'max_downloads': max_downloads,
        'downloads': 0,
        'expiry_time': expiry_time.isoformat()
    }
    save_metadata(metadata)

    return jsonify({'code': code}), 200

def download_file(code):
    metadata = load_metadata()

    if code not in metadata:
        return render_template('error.html',
            error_title='Invalid Code',
            error_message='The code you entered is invalid or incorrect. Please check your code and try again.'
        ), 404

    file_info = metadata[code]
    file_path = file_info['path']
    expiry_time = datetime.fromisoformat(file_info['expiry_time'])

    # Check expiry
    if datetime.now() > expiry_time:
        del metadata[code]
        save_metadata(metadata)
        return render_template('error.html',
            error_title='File Expired',
            error_message='This file has expired and is no longer available for download.'
        ), 404

    # Check if file exists
    if not os.path.exists(file_path):
        del metadata[code]
        save_metadata(metadata)
        return render_template('error.html',
            error_title='File Not Found',
            error_message='The requested file could not be found on the server.'
        ), 404

    # Increment download counter before checking limit
    file_info['downloads'] += 1
    
    # Check if this download puts us over the limit
    if file_info['downloads'] > file_info['max_downloads']:
        # Clean up the file and metadata
        if os.path.exists(file_path):
            os.remove(file_path)
        del metadata[code]
        save_metadata(metadata)
        return render_template('error.html',
            error_title='Download Limit Reached',
            error_message='This file has reached its maximum number of downloads and is no longer available.'
        ), 404

    # Save the updated download count
    save_metadata(metadata)
    
    # Serve the file
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=file_info['filename']
    )

def delete_file(code):
    metadata = load_metadata()

    if code not in metadata:
        return jsonify({'error': 'Invalid code'}), 404

    file_info = metadata[code]
    file_path = file_info['path']
    expiry_time = datetime.fromisoformat(file_info['expiry_time'])

    # Check expiry
    if datetime.now() > expiry_time:
        del metadata[code]
        save_metadata(metadata)
        return jsonify({'error': 'File already expired'}), 404

    # Check if still downloadable
    if file_info['downloads'] > file_info['max_downloads']:
        del metadata[code]
        save_metadata(metadata)
        return jsonify({'error': 'File no longer available'}), 404

    # Delete the file
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove from metadata
    del metadata[code]
    save_metadata(metadata)
    log.i(f"File deleted: {code}")
    
    return jsonify({'message': 'File deleted successfully'}), 200

def cleanup_expired_files():
    metadata = load_metadata()
    updated_metadata = {}

    for code, file_info in metadata.items():
        expiry_time = datetime.fromisoformat(file_info['expiry_time'])
        if datetime.now() > expiry_time or file_info['downloads'] >= file_info['max_downloads']:
            # Remove the file if it exists
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
        else:
            updated_metadata[code] = file_info

    save_metadata(updated_metadata)
    log.i("Cleanup completed: Expired and overused files removed.")

def start_chunked_upload():
    # Get metadata from request
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    total_chunks = request.form.get('total_chunks')
    if not total_chunks or not total_chunks.isdigit():
        return jsonify({'error': 'Invalid total_chunks parameter'}), 400
    
    # Generate unique upload ID and create chunk directory
    upload_id = generate_upload_id()
    chunk_dir = os.path.join(CHUNKS_FOLDER, upload_id)
    os.makedirs(chunk_dir)
    
    # Store upload session metadata
    metadata = load_chunk_metadata()
    metadata[upload_id] = {
        'filename': secure_filename(filename),
        'total_chunks': int(total_chunks),
        'received_chunks': [],
        'created_at': datetime.now().isoformat(),
        'chunk_dir': chunk_dir,
        'max_downloads': int(request.form.get('max_downloads', 1)),
        'expiry_hours': int(request.form.get('expiry_hours', 24))
    }
    save_chunk_metadata(metadata)
    
    log.i(f"Started chunked upload session: {upload_id}")
    return jsonify({'upload_id': upload_id}), 200

def upload_chunk():
    # Validate parameters
    upload_id = request.form.get('upload_id')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')
    
    if not upload_id or not chunk_index or not chunk_index.isdigit():
        log.e(f"Invalid chunk upload parameters: upload_id={upload_id}, chunk_index={chunk_index}")
        return jsonify({'error': 'Invalid parameters'}), 400
    
    chunk_index = int(chunk_index)
    
    # Get upload session metadata
    metadata = load_chunk_metadata()
    if upload_id not in metadata:
        log.e(f"Invalid upload session ID: {upload_id}")
        return jsonify({'error': 'Invalid upload session'}), 404
    
    session = metadata[upload_id]
    
    # Validate chunk index
    if chunk_index >= session['total_chunks']:
        log.e(f"Invalid chunk index: {chunk_index}, total_chunks: {session['total_chunks']}")
        return jsonify({'error': 'Invalid chunk index'}), 400
    
    # Handle the chunk file
    if 'chunk' not in request.files:
        log.e(f"No chunk file provided for chunk {chunk_index} of upload {upload_id}")
        return jsonify({'error': 'No chunk file provided'}), 400
    
    chunk_file = request.files['chunk']
    if chunk_file.filename == '':
        log.e(f"Empty chunk file for chunk {chunk_index} of upload {upload_id}")
        return jsonify({'error': 'Empty chunk file'}), 400
    
    # Save the chunk
    chunk_path = os.path.join(session['chunk_dir'], f'chunk_{chunk_index}')
    chunk_file.save(chunk_path)
    
    # Verify the chunk was saved successfully
    if not os.path.exists(chunk_path) or os.path.getsize(chunk_path) == 0:
        log.e(f"Failed to save chunk {chunk_index} for upload {upload_id}")
        return jsonify({'error': 'Failed to save chunk'}), 500
    
    # Update metadata
    if chunk_index not in session['received_chunks']:
        session['received_chunks'].append(chunk_index)
        log.i(f"Added chunk {chunk_index} to received_chunks list for upload {upload_id}")
    else:
        log.w(f"Chunk {chunk_index} already in received_chunks list for upload {upload_id}, possible duplicate")
    
    metadata[upload_id] = session
    save_chunk_metadata(metadata)
    
    # If client sent total_chunks, validate it matches what we have
    if total_chunks and total_chunks.isdigit() and int(total_chunks) != session['total_chunks']:
        log.w(f"Client reported total_chunks ({total_chunks}) doesn't match server ({session['total_chunks']})")
    
    log.i(f"Received chunk {chunk_index} for upload {upload_id}, now have {len(session['received_chunks'])}/{session['total_chunks']}")
    return jsonify({
        'success': True,
        'received_chunks': len(session['received_chunks']),
        'total_chunks': session['total_chunks'],
        'chunk_index': chunk_index
    }), 200

def complete_chunked_upload():
    upload_id = request.form.get('upload_id')
    if not upload_id:
        return jsonify({'error': 'Upload ID is required'}), 400
    
    # Get upload session metadata
    metadata = load_chunk_metadata()
    if upload_id not in metadata:
        return jsonify({'error': 'Invalid upload session'}), 404
    
    session = metadata[upload_id]
    
    # Verify all chunks are received by checking if every expected chunk index is in received_chunks
    expected_chunks = set(range(session['total_chunks']))
    received_chunks = set(session['received_chunks'])
    if expected_chunks != received_chunks:
        missing_chunks = list(expected_chunks - received_chunks)
        log.e(f"Missing chunks for upload {upload_id}: {missing_chunks}")
        return jsonify({
            'error': 'Not all chunks received',
            'received': len(session['received_chunks']),
            'total': session['total_chunks'],
            'missing_chunks': missing_chunks
        }), 400
    
    # Combine chunks into final file
    final_filename = session['filename']
    final_path = os.path.join(UPLOAD_FOLDER, final_filename)
    
    # Verify all chunk files actually exist on disk
    missing_files = []
    for i in range(session['total_chunks']):
        chunk_path = os.path.join(session['chunk_dir'], f'chunk_{i}')
        if not os.path.exists(chunk_path):
            missing_files.append(i)
    
    if missing_files:
        log.e(f"Missing chunk files for upload {upload_id} despite being in received_chunks: {missing_files}")
        return jsonify({
            'error': 'Chunk files missing on server',
            'missing_files': missing_files
        }), 500
    
    with open(final_path, 'wb') as outfile:
        for i in range(session['total_chunks']):
            chunk_path = os.path.join(session['chunk_dir'], f'chunk_{i}')
            with open(chunk_path, 'rb') as infile:
                outfile.write(infile.read())
    
    # Clean up chunks
    import shutil
    shutil.rmtree(session['chunk_dir'])
    del metadata[upload_id]
    save_chunk_metadata(metadata)
    
    # Create regular file metadata
    code = generate_unique_code()
    expiry_time = datetime.now() + timedelta(hours=session['expiry_hours'])
    
    file_metadata = load_metadata()
    file_metadata[code] = {
        'filename': final_filename,
        'path': final_path,
        'max_downloads': session['max_downloads'],
        'downloads': 0,
        'expiry_time': expiry_time.isoformat()
    }
    save_metadata(file_metadata)
    
    log.i(f"Completed chunked upload {upload_id}, assigned code {code}")
    return jsonify({'code': code}), 200

def cleanup_abandoned_uploads():
    metadata = load_chunk_metadata()
    current_time = datetime.now()
    expired_uploads = []
    
    for upload_id, session in metadata.items():
        created_at = datetime.fromisoformat(session['created_at'])
        # Remove uploads older than 24 hours
        if (current_time - created_at).total_seconds() > 86400:
            if os.path.exists(session['chunk_dir']):
                shutil.rmtree(session['chunk_dir'])
            expired_uploads.append(upload_id)
    
    for upload_id in expired_uploads:
        del metadata[upload_id]
    
    if expired_uploads:
        save_chunk_metadata(metadata)
        log.i(f"Cleaned up {len(expired_uploads)} abandoned uploads")

def verify_chunks():
    """Verify which chunks have been received for an upload session"""
    # Get upload ID from request
    upload_id = request.form.get('upload_id')
    
    if not upload_id:
        return jsonify({'error': 'Upload ID is required'}), 400
    
    # Get upload session metadata
    metadata = load_chunk_metadata()
    if upload_id not in metadata:
        return jsonify({'error': 'Invalid upload session'}), 404
    
    session = metadata[upload_id]
    
    # Calculate missing chunks
    received_chunks = set(session['received_chunks'])
    all_chunks = set(range(session['total_chunks']))
    missing_chunks = list(all_chunks - received_chunks)
    
    # Check for each chunk file on disk to verify it actually exists
    disk_missing_chunks = []
    for chunk_index in range(session['total_chunks']):
        chunk_path = os.path.join(session['chunk_dir'], f'chunk_{chunk_index}')
        if not os.path.exists(chunk_path):
            disk_missing_chunks.append(chunk_index)
            # If it's in received_chunks but not on disk, there was a problem
            if chunk_index in received_chunks:
                log.w(f"Chunk {chunk_index} marked as received but file is missing for upload {upload_id}")
                # Remove from received_chunks since the file is missing
                if chunk_index in session['received_chunks']:
                    session['received_chunks'].remove(chunk_index)
    
    # Update metadata if any changes were made
    if len(received_chunks) != len(session['received_chunks']):
        metadata[upload_id] = session
        save_chunk_metadata(metadata)
    
    # Return missing chunks information
    log.i(f"Verified chunks for upload {upload_id}: {len(session['received_chunks'])}/{session['total_chunks']} received")
    
    # Final verification
    missing_chunks = list(all_chunks - set(session['received_chunks']))
    
    return jsonify({
        'total_chunks': session['total_chunks'],
        'received_chunks': len(session['received_chunks']),
        'missing_chunks': missing_chunks
    }), 200