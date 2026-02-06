"""
Static pages routes for Discussion Den
Handles About, Privacy, Terms, and Help pages
"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__, url_prefix="/pages")


@pages_bp.get("/about")
def about():
    """About Discussion Den page"""
    return render_template("pages/about.html")


@pages_bp.get("/privacy")
def privacy():
    """Privacy Policy page"""
    return render_template("pages/privacy.html")


@pages_bp.get("/terms")
def terms():
    """Terms of Service page"""
    return render_template("pages/terms.html")


@pages_bp.get("/help")
def help_page():
    """Help & Support page"""
    return render_template("pages/help.html")
