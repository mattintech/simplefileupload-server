import os
from flask import Blueprint, render_template

views = Blueprint('views', __name__)

def get_version():
    version_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'version.txt')
    try:
        with open(version_path) as f:
            return f.read().strip()
    except:
        return '0.0.0'

@views.route('/')
def home():
    return render_template('index.html', version=get_version())