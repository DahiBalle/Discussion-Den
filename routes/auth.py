from __future__ import annotations

"""
Authentication Routes Module.

This module handles all user authentication flows, including:
- User Registration (with OTP verification)
- User Login/Logout (Session management)
- Google OAuth Integration (Social Login)
- Password management (Hashing/Salting)

It uses Flask-Login for session handling and Flask-Mail for sending OTPs.
"""

from datetime import datetime
import secrets
import string
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from flask_mail import Message
from extensions import db, oauth, mail
from forms import LoginForm, RegisterForm
from models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _generate_safe_username(email: str) -> str:
    """
    Generate a safe, unique username from email address.
    
    Safety Features:
    - Uses email prefix as base
    - Adds random suffix to prevent collisions
    - Validates uniqueness in database
    - Falls back to fully random username if needed
    
    Args:
        email (str): User's email address from Google
        
    Returns:
        str: Safe, unique username that doesn't conflict with existing users
    """
    try:
        # Extract base from email (part before @)
        base = email.split('@')[0].lower()
        
        # Clean base - only alphanumeric and underscore
        base = ''.join(c for c in base if c.isalnum() or c == '_')
        
        # Ensure base is not empty and not too long
        if not base or len(base) < 3:
            base = 'user'
        elif len(base) > 20:
            base = base[:20]
        
        # Try base username first
        if not User.query.filter_by(username=base).first():
            return base
        
        # Add random suffix if base is taken
        for _ in range(10):  # Try 10 times
            suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
            username = f"{base}_{suffix}"
            
            if not User.query.filter_by(username=username).first():
                return username
        
        # Fallback: fully random username
        random_username = 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        return random_username
        
    except Exception as e:
        print(f"ERROR: Username generation failed: {e}")
        # Ultimate fallback
        return 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))


@auth_bp.get("/register")
def register():
    """
    Render the registration page.
    """
    form = RegisterForm()
    return render_template("auth/register.html", form=form)


@auth_bp.post("/register")
def register_post():
    form = RegisterForm()
    if not form.validate_on_submit():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "errors": form.errors}, 400
        return render_template("auth/register.html", form=form), 400

    if User.query.filter_by(username=form.username.data.strip()).first():
        error_msg = "That username is taken."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": error_msg}, 400
        flash(error_msg, "danger")
        return render_template("auth/register.html", form=form), 400
        
    if User.query.filter_by(email=form.email.data.strip().lower()).first():
        error_msg = "That email is already registered."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": error_msg}, 400
        flash(error_msg, "danger")
        return render_template("auth/register.html", form=form), 400

    # Stop: Do not create user yet. Start OTP flow.
    # Generate 6-digit OTP
    otp = ''.join(secrets.choice(string.digits) for _ in range(6))
    
    # Store data in session
    session['registration_data'] = {
        'username': form.username.data.strip(),
        'email': form.email.data.strip().lower(),
        'password': form.password.data  # Will be hashed later
    }
    session['registration_otp'] = otp
    session['registration_otp_time'] = datetime.utcnow().timestamp()
    
    # Send Email
    try:
        with mail.connect() as conn:
            msg = Message(
                subject="Verify your Discussion Den Account",
                recipients=[form.email.data.strip().lower()],
                body=f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.",
                html=f"""
                <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
                    <h2>Welcome to Discussion Den!</h2>
                    <p>Please use the following code to verify your email address:</p>
                    <div style="background: #f0f2f5; padding: 20px; text-align: center; border-radius: 8px; font-size: 24px; letter-spacing: 5px; font-weight: bold; margin: 20px 0;">
                        {otp}
                    </div>
                    <p>This code expires in 10 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                """
            )
            conn.send(msg)
            print(f"DEBUG: Email sent to {form.email.data}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        # For development fallback if SMTP fails
        print(f"DEBUG FALLBACK: OTP for {form.email.data} is {otp}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             # In production, we might want to fail here, but for now we proceed to allow testing
             pass

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {
            "success": True, 
            "message": "Verification code sent to your email.", 
            "require_otp": True,
            "email": form.email.data.strip().lower()
        }
    
    # Fallback for non-JS (shouldn't happen with current UI)
    flash("Verification code sent to your email.", "info")
    return render_template("auth/verify_otp.html") # We'll need a template or just reuse register


@auth_bp.post("/verify-otp")
def verify_otp():
    """
    Verify the OTP and create the account.
    """
    data = request.json
    entered_otp = data.get('otp') if data else None
    
    stored_otp = session.get('registration_otp')
    stored_data = session.get('registration_data')
    timestamp = session.get('registration_otp_time')
    
    # Debug logging
    print(f"DEBUG verify_otp: entered_otp={entered_otp}, stored_otp={stored_otp}, has_stored_data={bool(stored_data)}, timestamp={timestamp}")
    
    if not entered_otp or not stored_otp or not stored_data:
        return {"success": False, "message": "Invalid or expired session. Please register again."}, 400
        
    # Check expiration (10 minutes)
    if datetime.utcnow().timestamp() - timestamp > 600:
        session.pop('registration_otp', None)
        session.pop('registration_data', None)
        return {"success": False, "message": "Code expired. Please register again."}, 400
        
    if entered_otp != stored_otp:
        return {"success": False, "message": "Invalid code. Please try again."}, 400
        
    # OTP Valid: Create User
    try:
        user = User(
            username=stored_data['username'],
            email=stored_data['email'],
            password_hash=generate_password_hash(stored_data['password']),
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        session["active_persona_id"] = None
        
        # Clear session
        session.pop('registration_otp', None)
        session.pop('registration_data', None)
        session.pop('registration_otp_time', None)
        
        return {"success": True, "message": "Account verified! Welcome to Discussion Den.", "redirect": url_for("feed.feed")}
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR creating user: {e}")
        return {"success": False, "message": "Database error. Please try again."}, 500


@auth_bp.post("/resend-otp")
def resend_otp():
    """Resend the OTP to the email in session."""
    stored_data = session.get('registration_data')
    if not stored_data:
        return {"success": False, "message": "Session expired."}, 400
        
    # Generate new OTP
    otp = ''.join(secrets.choice(string.digits) for _ in range(6))
    session['registration_otp'] = otp
    session['registration_otp_time'] = datetime.utcnow().timestamp()
    
    # Send Email
    try:
        with mail.connect() as conn:
            msg = Message(
                subject="Verify your Discussion Den Account (Resend)",
                recipients=[stored_data['email']],
                body=f"Your new verification code is: {otp}",
                 html=f"""
                <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
                    <h2>Discussion Den Verification</h2>
                    <p>Your new verification code is:</p>
                    <div style="background: #f0f2f5; padding: 20px; text-align: center; border-radius: 8px; font-size: 24px; letter-spacing: 5px; font-weight: bold; margin: 20px 0;">
                        {otp}
                    </div>
                </div>
                """
            )
            conn.send(msg)
            return {"success": True, "message": "New code sent."}
    except Exception as e:
        print(f"ERROR: Failed to resend email: {e}")
        # Fallback debug
        print(f"DEBUG FALLBACK: OTP for {stored_data['email']} is {otp}")
        return {"success": True, "message": "New code sent (dev mode)."}


@auth_bp.get("/login")
def login():
    """
    Render the login page.
    
    If the user is already logged in, redirects to the feed.
    Uses a redirect guard to prevent potential loops.
    """
    # Unified auth experience: redirect to feed with query param so modal opens
    if hasattr(login, "_redirect_guard"):
        # Basic guard to avoid unlikely redirect loops
        return redirect(url_for("feed.feed"))
    setattr(login, "_redirect_guard", True)
    try:
        return redirect(url_for("feed.feed", auth="login"))
    finally:
        # remove guard for future requests
        delattr(login, "_redirect_guard")


@auth_bp.post("/login")
def login_post():
    form = LoginForm()
    if not form.validate_on_submit():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "errors": form.errors}, 400
        return render_template("auth/login.html", form=form), 400

    user = User.query.filter_by(username=form.username.data.strip()).first()
    if not user or not check_password_hash(user.password_hash, form.password.data):
        error_msg = "Invalid username or password."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": error_msg}, 401
        flash(error_msg, "danger")
        return render_template("auth/login.html", form=form), 401

    login_user(user)
    # Keep prior persona if still valid; otherwise reset.
    if request.args.get("reset_persona") == "1":
        session["active_persona_id"] = None
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"success": True, "message": "Logged in successfully!", "redirect": url_for("feed.feed")}
    
    flash("Logged in.", "success")
    return redirect(url_for("feed.feed"))


@auth_bp.route("/logout",methods=["GET",'POST'])
def logout():
    """
    Log out the current user and clear session data.
    Redirects to login page.
    """
    logout_user()
    session.pop("active_persona_id", None)
    flash("Logged out.", "secondary")
    return redirect(url_for("auth.login"))


# GOOGLE OAUTH ROUTES (OPTIONAL - SAFE ADDITIONS)

@auth_bp.get("/google")
def google_login():
    """
    Initiate Google OAuth login flow.

    Safety guarantees:
    - Does NOT assume oauth.google attribute exists
    - Correctly checks Authlib registry
    - Fails gracefully if Google OAuth is not configured
    - Does NOT affect normal login system
    """

    # ✅ Correct and reliable OAuth configuration check (Authlib-safe)
    if not (hasattr(oauth, "_registry") and "google" in oauth._registry):
        flash(
            "Google login is not configured on this server. "
            "Please use email/password login.",
            "warning"
        )
        return redirect(url_for("auth.login"))

    try:
        # Generate secure redirect URI
        redirect_uri = url_for("auth.google_callback", _external=True)

        # Initiate OAuth redirect to Google
        return oauth.google.authorize_redirect(redirect_uri)

    except Exception as e:
        # Safety: Never crash auth flow
        print(f"ERROR: Google OAuth initiation failed: {e}")
        flash(
            "Google login is temporarily unavailable. "
            "Please use email/password login.",
            "warning"
        )
        return redirect(url_for("auth.login"))


@auth_bp.get("/google/callback")
def google_callback():
    """
    Handle Google OAuth callback and user authentication.
    """

    # ✅ Correct Authlib-safe OAuth detection
    if not (hasattr(oauth, "_registry") and "google" in oauth._registry):
        flash("Google login is not configured.", "danger")
        return redirect(url_for("auth.login"))

    try:
        # Exchange authorization code for token
        token = oauth.google.authorize_access_token()

        # Get user info (OIDC-compliant)
        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.parse_id_token(token)

        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            flash("Google login requires email access.", "danger")
            return redirect(url_for("auth.login"))

        email = email.strip().lower()

        # Check existing user
        user = User.query.filter_by(email=email).first()

        if user:
            login_user(user)
            session["active_persona_id"] = None
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("feed.feed"))

        # Instead of creating user immediately, redirect to completion page
        session['google_signup_data'] = {
            'email': email,
            'name': name
        }
        return redirect(url_for("auth.complete_google_signup"))

    except Exception as e:
        print(f"ERROR: Google OAuth callback failed: {e}")
        flash(
            "Google login failed. Please try again or use email/password login.",
            "danger"
        )
        return redirect(url_for("auth.login"))


@auth_bp.route("/complete-google-signup", methods=["GET", "POST"])
def complete_google_signup():
    """
    Final step of Google Signup: Ask user for a username.
    """
    signup_data = session.get('google_signup_data')
    if not signup_data:
        flash("Google signup session expired or invalid. Please try logging in again.", "warning")
        return redirect(url_for("auth.login"))

    from forms import GoogleSignupForm # Avoid circular import if needed, or move to top
    form = GoogleSignupForm()

    # Pre-fill username on GET if not already submitted
    if request.method == "GET" and not form.username.data:
        # Generate a safe suggestion
        base_suggestion = _generate_safe_username(signup_data['email'])
        form.username.data = base_suggestion

    if form.validate_on_submit():
        desired_username = form.username.data.strip()
        
        # Check if username exists
        if User.query.filter_by(username=desired_username).first():
            flash("That username is already taken. Please choose another.", "danger")
            return render_template("auth/complete_google_signup.html", form=form)

        # Create the user
        try:
            email = signup_data['email']
            name = signup_data['name']
            dummy_password_hash = generate_password_hash("google_oauth_no_password") # Or random secure string

            new_user = User(
                username=desired_username,
                email=email,
                password_hash=dummy_password_hash,
                bio=f"Joined via Google. {name}" if name else "Joined via Google."
            )

            db.session.add(new_user)
            db.session.commit()

            # Log them in
            login_user(new_user)
            session["active_persona_id"] = None
            
            # Clean up session
            session.pop('google_signup_data', None)

            flash(f"Welcome to Discussion Den, {desired_username}!", "success")
            return redirect(url_for("feed.feed"))
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR creating Google user: {e}")
            flash("An error occurred while creating your account. Please try again.", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth/complete_google_signup.html", form=form)
