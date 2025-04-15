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

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'tmp/uploads'
app.config['CLIENT_KEY'] = os.getenv('CLIENT_KEY', 'default-secret-key')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def require_client_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_key = request.headers.get('X-Client-Key')
        if not client_key or client_key != app.config['CLIENT_KEY']:
            log.e("Invalid or missing client key")
            return jsonify({'error': 'Invalid or missing client key'}), 401
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