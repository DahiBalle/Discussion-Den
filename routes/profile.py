from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import EditProfileForm
from models import Persona, User


profile_bp = Blueprint("profile", __name__)


@profile_bp.get("/u/<username>")
@login_required
def user_profile(username: str):
    from models import Post
    user = User.query.filter_by(username=username).first_or_404()
    public_personas = Persona.query.filter_by(user_id=user.id, is_public=True).all()
    user_posts = Post.query.filter_by(author_user_id=user.id).order_by(Post.created_at.desc()).limit(20).all()
    is_owner = current_user.is_authenticated and current_user.id == user.id
    return render_template(
        "user_profile.html",
        user=user,
        public_personas=public_personas,
        user_posts=user_posts,
        is_owner=is_owner,
    )


@profile_bp.get("/edit-profile")
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    return render_template("edit_profile.html", form=form)


@profile_bp.post("/edit-profile")
@login_required
def edit_profile_post():
    form = EditProfileForm()
    if not form.validate_on_submit():
        return render_template("edit_profile.html", form=form), 400

    current_user.avatar = form.avatar.data.strip() if form.avatar.data else None
    current_user.bio = form.bio.data.strip() if form.bio.data else None
    db.session.commit()

    flash("Profile updated.", "success")
    return redirect(url_for("profile.user_profile", username=current_user.username))


@profile_bp.post("/create-persona")
@login_required
def create_persona_quick():
    """
    Minimal persona creation for demo UX: creates a public persona with a default name.
    Edit details on the persona edit page.
    """
    name = f"{current_user.username}'s Persona"
    persona = Persona(user_id=current_user.id, name=name, is_public=True)
    db.session.add(persona)
    db.session.commit()

    flash("Persona created. Customize it any time.", "success")
    return redirect(url_for("persona.persona_profile", persona_id=persona.id))


@profile_bp.get("/_forbidden")
def forbidden():
    abort(403)

