from __future__ import annotations

import secrets
import string
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, oauth
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
    form = RegisterForm()
    return render_template("auth/register.html", form=form)


@auth_bp.post("/register")
def register_post():
    form = RegisterForm()
    if not form.validate_on_submit():
        return render_template("auth/register.html", form=form), 400

    if User.query.filter_by(username=form.username.data.strip()).first():
        flash("That username is taken.", "danger")
        return render_template("auth/register.html", form=form), 400
    if User.query.filter_by(email=form.email.data.strip().lower()).first():
        flash("That email is already registered.", "danger")
        return render_template("auth/register.html", form=form), 400

    user = User(
        username=form.username.data.strip(),
        email=form.email.data.strip().lower(),
        password_hash=generate_password_hash(form.password.data),
    )
    db.session.add(user)
    db.session.commit()

    login_user(user)
    session["active_persona_id"] = None
    flash("Welcome! Your account is ready.", "success")
    return redirect(url_for("feed.feed"))


@auth_bp.get("/login")
def login():
    form = LoginForm()
    return render_template("auth/login.html", form=form)


@auth_bp.post("/login")
def login_post():
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("auth/login.html", form=form), 400

    user = User.query.filter_by(username=form.username.data.strip()).first()
    if not user or not check_password_hash(user.password_hash, form.password.data):
        flash("Invalid username or password.", "danger")
        return render_template("auth/login.html", form=form), 401

    login_user(user)
    # Keep prior persona if still valid; otherwise reset.
    if request.args.get("reset_persona") == "1":
        session["active_persona_id"] = None
    flash("Logged in.", "success")
    return redirect(url_for("feed.feed"))


@auth_bp.route("/logout",methods=["GET",'POST'])
def logout():
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

        # Create new user
        username = _generate_safe_username(email)
        dummy_password_hash = generate_password_hash("google_oauth_no_password")

        new_user = User(
            username=username,
            email=email,
            password_hash=dummy_password_hash,
            bio=f"Joined via Google. {name}" if name else "Joined via Google."
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        session["active_persona_id"] = None
        flash(f"Welcome to Discussion Den, {username}!", "success")
        return redirect(url_for("feed.feed"))

    except Exception as e:
        print(f"ERROR: Google OAuth callback failed: {e}")
        flash(
            "Google login failed. Please try again or use email/password login.",
            "danger"
        )
        return redirect(url_for("auth.login"))
