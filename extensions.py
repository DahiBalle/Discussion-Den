"""
Flask extensions module.

Why: Separates extension initialization from app creation to avoid circular imports.
Routes and models can import db, login_manager, csrf from here without importing app.py.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Initialize extensions (will be bound to app in create_app())
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
