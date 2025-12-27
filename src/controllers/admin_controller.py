import os
import pyotp
import qrcode
import io
import base64
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, render_template, session, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import utils.mLogger as log
from models import get_admin, create_admin, model_admin_exists, update_last_login

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
    """Display admin dashboard with client key"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    client_key = current_app.config.get('CLIENT_KEY', 'Not configured')
    username = session.get('admin_username', 'Admin')

    return render_template('admin_dashboard.html',
                         client_key=client_key,
                         username=username)

def admin_logout():
    """Handle admin logout"""
    username = session.get('admin_username', 'Unknown')
    session.pop('admin_authenticated', None)
    session.pop('admin_username', None)
    log.i(f"Admin user logged out: {username}")
    return redirect(url_for('admin_login'))
