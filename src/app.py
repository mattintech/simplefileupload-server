import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import utils.mLogger as log

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'tmp/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# TinyURL API for generating short URLs
def generate_tiny_url(long_url):
    response = requests.get(f'http://tinyurl.com/api-create.php?url={long_url}')
    return response.text if response.status_code == 200 else None

# Route for file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        log.e("No File Part")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        log.e("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    log.i(f"File upload: {file_path}")
    file.save(file_path)

    # Generate a download link
    download_url = request.host_url + 'download/' + filename
    tiny_url = generate_tiny_url(download_url)

    return jsonify({'tiny_url': tiny_url}), 200

# Route for downloading the file (one-time)
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        # Serve the file and then delete it
        response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        os.remove(file_path)
        return response
    else:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    log.i("Running flask in debug...")
    app.run(debug=True, host="0.0.0.0", port=7777)