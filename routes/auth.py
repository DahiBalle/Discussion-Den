from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from forms import LoginForm, RegisterForm
from models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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


@auth_bp.post("/logout")
def logout():
    logout_user()
    session.pop("active_persona_id", None)
    flash("Logged out.", "secondary")
    return redirect(url_for("auth.login"))

