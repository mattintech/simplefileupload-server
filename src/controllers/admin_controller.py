import os
import pyotp
import qrcode
import io
import base64
import json
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, render_template, session, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import utils.mLogger as log
from models import (
    get_admin, create_admin, model_admin_exists, update_last_login,
    get_config, update_server_address, update_server_port, regenerate_client_key
)

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            log.w("Unauthorized admin access attempt")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_exists():
    """Check if an admin user has been created"""
    return model_admin_exists()

def setup_admin():
    """Handle initial admin setup - Step 1: Username and Password"""
    if admin_exists():
        log.w("Attempted to access setup page when admin already exists")
        return redirect(url_for('admin_login'))

    if request.method == 'GET':
        return render_template('admin_setup.html')

    # POST request - validate and store credentials in session
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not username or not password or not confirm_password:
        return render_template('admin_setup.html', error='All fields are required')

    if password != confirm_password:
        return render_template('admin_setup.html', error='Passwords do not match')

    if len(password) < 8:
        return render_template('admin_setup.html', error='Password must be at least 8 characters')

    # Store credentials in session temporarily
    session['temp_username'] = username
    session['temp_password_hash'] = generate_password_hash(password, method='pbkdf2:sha256')

    log.i(f"Admin credentials created for: {username}, proceeding to TOTP setup")
    return redirect(url_for('setup_admin_totp'))

def setup_admin_totp():
    """Handle TOTP setup - Step 2: Configure Two-Factor Authentication"""
    if admin_exists():
        log.w("Attempted to access TOTP setup when admin already exists")
        return redirect(url_for('admin_login'))

    # Check if step 1 was completed
    if 'temp_username' not in session:
        log.w("Attempted to access TOTP setup without completing step 1")
        return redirect(url_for('setup_admin'))

    username = session.get('temp_username')

    if request.method == 'GET':
        # Generate TOTP secret
        totp_secret = pyotp.random_base32()
        session['temp_totp_secret'] = totp_secret

        # Generate QR code for TOTP setup
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
            name=username,
            issuer_name='Simple File Server'
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert QR code to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return render_template('admin_setup_totp.html',
                             qr_code=qr_base64,
                             totp_secret=totp_secret,
                             username=username)

    # POST request - verify TOTP and complete setup
    totp_code = request.form.get('totp_code')
    totp_secret = session.get('temp_totp_secret')
    password_hash = session.get('temp_password_hash')

    if not totp_code:
        # Regenerate QR code for error response
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
            name=username,
            issuer_name='Simple File Server'
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return render_template('admin_setup_totp.html',
                             error='TOTP code is required',
                             qr_code=qr_base64,
                             totp_secret=totp_secret,
                             username=username)

    # Verify TOTP code
    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        log.w(f"Failed admin setup: invalid TOTP code for user '{username}'")

        # Regenerate QR code for error response
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
            name=username,
            issuer_name='Simple File Server'
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return render_template('admin_setup_totp.html',
                             error='Invalid TOTP code. Please check your authenticator app and try again.',
                             qr_code=qr_base64,
                             totp_secret=totp_secret,
                             username=username)

    # TOTP verified - create admin account
    create_admin(username, password_hash, totp_secret)

    # Clean up session
    session.pop('temp_username', None)
    session.pop('temp_password_hash', None)
    session.pop('temp_totp_secret', None)

    log.i(f"Admin user created: {username}")

    return render_template('admin_setup_complete.html', username=username)

def admin_login():
    """Handle admin login"""
    if not admin_exists():
        return redirect(url_for('setup_admin'))

    if session.get('admin_authenticated'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'GET':
        return render_template('admin_login.html')

    # POST request - authenticate
    username = request.form.get('username')
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')

    if not username or not password or not totp_code:
        return render_template('admin_login.html', error='All fields are required')

    admin_data = get_admin()

    if not admin_data:
        log.e("Admin data not found during login attempt")
        return render_template('admin_login.html', error='Invalid credentials')

    # Verify username and password
    if username != admin_data['username']:
        log.w(f"Failed login attempt: invalid username '{username}'")
        return render_template('admin_login.html', error='Invalid credentials')

    if not check_password_hash(admin_data['password_hash'], password):
        log.w(f"Failed login attempt: invalid password for user '{username}'")
        return render_template('admin_login.html', error='Invalid credentials')

    # Verify TOTP
    totp = pyotp.TOTP(admin_data['totp_secret'])
    if not totp.verify(totp_code, valid_window=1):
        log.w(f"Failed login attempt: invalid TOTP code for user '{username}'")
        return render_template('admin_login.html', error='Invalid TOTP code')

    # Authentication successful
    session['admin_authenticated'] = True
    session['admin_username'] = username
    session.permanent = True

    # Update last login time
    update_last_login(username)

    log.i(f"Admin user logged in: {username}")

    return redirect(url_for('admin_dashboard'))

def admin_dashboard():
    """Display admin dashboard with client key and QR code"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    # Get server configuration from database
    config = get_config()

    if not config:
        log.e("Server configuration not found in database")
        return render_template('admin_dashboard.html',
                             error='Server configuration error',
                             username=session.get('admin_username', 'Admin'))

    client_key = config['client_key']
    server_address = config.get('server_address') or ''
    server_port = config.get('server_port') or 7777
    username = session.get('admin_username', 'Admin')

    # Generate QR code if server address and port are configured
    qr_code_base64 = None
    if server_address and server_port:
        qr_code_base64 = generate_config_qr(server_address, server_port, client_key)

    return render_template('admin_dashboard.html',
                         client_key=client_key,
                         server_address=server_address,
                         server_port=server_port,
                         qr_code=qr_code_base64,
                         username=username,
                         success=request.args.get('success'),
                         error=request.args.get('error'))

def admin_logout():
    """Handle admin logout"""
    username = session.get('admin_username', 'Unknown')
    session.pop('admin_authenticated', None)
    session.pop('admin_username', None)
    log.i(f"Admin user logged out: {username}")
    return redirect(url_for('admin_login'))


def generate_config_qr(server_address, server_port, client_key):
    """Generate QR code containing server configuration

    Args:
        server_address: Server IP or hostname
        server_port: Server port number
        client_key: Client authentication key

    Returns:
        str: Base64-encoded PNG image of QR code
        None: If error occurred
    """
    try:
        # Create JSON configuration
        config_data = {
            "server": server_address,
            "port": server_port,
            "key": client_key
        }
        config_json = json.dumps(config_data)

        # Generate QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(config_json)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return qr_base64
    except Exception as e:
        log.e(f"Error generating QR code: {e}")
        return None


@require_admin_auth
def update_config():
    """Handle server configuration updates from admin dashboard"""
    if request.method != 'POST':
        return redirect(url_for('admin_dashboard'))

    server_address = request.form.get('server_address', '').strip()
    server_port = request.form.get('server_port', '').strip()

    # Validate inputs
    if not server_address:
        return redirect(url_for('admin_dashboard', error='Server address is required'))

    try:
        port = int(server_port)
        if port < 1 or port > 65535:
            raise ValueError("Port out of range")
    except (ValueError, TypeError):
        return redirect(url_for('admin_dashboard', error='Invalid port number'))

    # Update database
    if not update_server_address(server_address):
        return redirect(url_for('admin_dashboard', error='Failed to update server address'))

    if not update_server_port(port):
        return redirect(url_for('admin_dashboard', error='Failed to update server port'))

    log.i(f"Server configuration updated: {server_address}:{port}")
    return redirect(url_for('admin_dashboard', success='Configuration updated successfully'))


@require_admin_auth
def regenerate_key():
    """Handle client key regeneration"""
    if request.method != 'POST':
        return redirect(url_for('admin_dashboard'))

    # Regenerate the key
    new_key = regenerate_client_key()

    if not new_key:
        return redirect(url_for('admin_dashboard', error='Failed to regenerate client key'))

    log.w(f"Client key regenerated by admin: {session.get('admin_username')}")
    return redirect(url_for('admin_dashboard', success='Client key regenerated successfully. All clients must update!'))
