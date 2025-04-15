import os
import random
import string
import json
from datetime import datetime, timedelta
from flask import request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
import utils.mLogger as log
from models.file_metadata import FileMetadata

# Make UPLOAD_FOLDER absolute
UPLOAD_FOLDER = os.path.abspath('tmp/uploads')
METADATA_FILE = 'file_metadata.json'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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