"""
Flask extensions module.

This module initializes the Flask extensions used throughout the application.
By initializing them here (unbound to the app), we avoid circular import issues
that would occur if we initialized them in app.py.

Extensions:
- SQLAlchemy: ORM for database interactions.
- LoginManager: Handles user session management.
- CSRFProtect: Protects forms against Cross-Site Request Forgery attacks.
- Mail: Handles email sending (e.g., for newsletters).
- OAuth: library for handling OAuth 1/2 authentication (used for Google Login).
- Limiter: strict rate limiting to prevent abuse.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Initialize extensions (will be bound to app in create_app())

# SQLAlchemy: The database ORM instance.
db = SQLAlchemy()

# LoginManager: Manages user login sessions.
login_manager = LoginManager()

# CSRFProtect: Enables CSRF protection globally for the app.
csrf = CSRFProtect()

# Mail: Instance for sending emails.
mail = Mail()

# OAuth: Registry for OAuth providers (e.g., Google).
# This allows users to log in using external accounts.
oauth = OAuth()

# Limiter: Rate limiter to protect routes from abuse.
# Uses the remote address (IP) to identify unique users.
# Default limits: 1000 requests per hour, 100 requests per minute.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)
