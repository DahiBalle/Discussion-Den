"""
Flask extensions module.

Why: Separates extension initialization from app creation to avoid circular imports.
Routes and models can import db, login_manager, csrf from here without importing app.py.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Initialize extensions (will be bound to app in create_app())
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
oauth = OAuth()  # Google OAuth integration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)
