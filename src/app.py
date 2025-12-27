import os
from functools import wraps
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import utils.mLogger as log
from controllers.file_controller import (
    upload_file, download_file, delete_file,
    start_chunked_upload, upload_chunk, verify_chunks, complete_chunked_upload,
    cleanup_expired_files, cleanup_abandoned_uploads
)
from controllers.admin_controller import (
    setup_admin, setup_admin_totp, admin_login, admin_dashboard, admin_logout
)
from views import views
from models import init_db, migrate_from_json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'tmp/uploads'
app.config['CLIENT_KEY'] = os.environ.get('CLIENT_KEY', 'default-secret-key')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize database
log.i("Initializing database...")
init_db()
migrate_from_json()

# Run cleanup on startup
cleanup_expired_files()
cleanup_abandoned_uploads()

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

# Routes for chunked uploads
app.route('/upload/start', methods=['POST'])(require_client_key(start_chunked_upload))
app.route('/upload/chunk', methods=['POST'])(require_client_key(upload_chunk))
app.route('/upload/verify', methods=['POST'])(require_client_key(verify_chunks))
app.route('/upload/complete', methods=['POST'])(require_client_key(complete_chunked_upload))

# Route for downloading the file
app.route('/download/<code>', methods=['GET'])(download_file)

# Route for deleting the file
app.route('/delete/<code>', methods=['DELETE'])(delete_file)

# Admin routes
app.route('/admin/setup', methods=['GET', 'POST'], endpoint='setup_admin')(setup_admin)
app.route('/admin/setup/totp', methods=['GET', 'POST'], endpoint='setup_admin_totp')(setup_admin_totp)
app.route('/admin/login', methods=['GET', 'POST'], endpoint='admin_login')(admin_login)
app.route('/admin', methods=['GET'], endpoint='admin_dashboard')(admin_dashboard)
app.route('/admin/logout', methods=['GET'], endpoint='admin_logout')(admin_logout)

# Register frontend views
app.register_blueprint(views)

if __name__ == '__main__':
    log.i("Running flask in debug...")
    app.run(debug=True, host="0.0.0.0", port=7777)