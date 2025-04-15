import os
import uuid
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv
import utils.mLogger as log
from controllers.file_controller import upload_file, download_file, delete_file
from views import views

# Get the project root directory (one level up from src)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')

# Load environment variables with explicit path
load_dotenv(dotenv_path=env_path)

# Debug log for environment loading
log.i(f"Loading .env from: {env_path}")
log.i(f"File exists: {os.path.exists(env_path)}")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'tmp/uploads'
app.config['CLIENT_KEY'] = os.getenv('CLIENT_KEY', 'default-secret-key')

# Log the loaded client key (masked)
if app.config['CLIENT_KEY']:
    masked_key = app.config['CLIENT_KEY'][:4] + '*' * (len(app.config['CLIENT_KEY']) - 4)
    log.i(f"Loaded client key: {masked_key}")
else:
    log.w("No client key configured, using default")

# Log all environment variables (masked)
for key, value in os.environ.items():
    if 'KEY' in key or 'SECRET' in key.upper():
        masked = value[:4] + '*' * (len(value) - 4) if value else None
        log.i(f"Env: {key}={masked}")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def require_client_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_key = request.headers.get('X-Client-Key')
        if not client_key:
            log.e("No client key provided in request headers")
            return jsonify({'error': 'Missing client key'}), 401
            
        expected_key = app.config['CLIENT_KEY']
        if client_key != expected_key:
            log.e(f"Invalid client key provided. Expected length: {len(expected_key)}, Got length: {len(client_key)}")
            return jsonify({'error': 'Invalid client key'}), 401
            
        log.i("Client key authentication successful")
        return f(*args, **kwargs)
    return decorated_function

# Route for file uploads
app.route('/upload', methods=['POST'])(require_client_key(upload_file))

# Route for downloading the file
app.route('/download/<code>', methods=['GET'])(download_file)

# Route for deleting the file
app.route('/delete/<code>', methods=['DELETE'])(delete_file)

app.register_blueprint(views)

if __name__ == '__main__':
    log.i("Running flask in debug...")
    app.run(debug=True, host="0.0.0.0", port=7777)