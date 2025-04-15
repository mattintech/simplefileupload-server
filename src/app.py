import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import utils.mLogger as log
from controllers.file_controller import upload_file, download_file
from views import views

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'tmp/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Route for file uploads
app.route('/upload', methods=['POST'])(upload_file)

# Route for downloading the file
app.route('/download/<code>', methods=['GET'])(download_file)

app.register_blueprint(views)

if __name__ == '__main__':
    log.i("Running flask in debug...")
    app.run(debug=True, host="0.0.0.0", port=7777)