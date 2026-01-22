from __future__ import annotations

from flask import Blueprint,abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import EditPersonaForm
from models import Persona, Post


persona_bp = Blueprint("persona", __name__)


@persona_bp.get("/persona/create")
@login_required
def create_persona():
    """Show form to create a new persona."""
    form = EditPersonaForm()
    return render_template("edit_persona.html", form=form, persona=None)


@persona_bp.post("/persona/create")
@login_required
def create_persona_post():
    """Create a new persona."""
    form = EditPersonaForm()
    if not form.validate_on_submit():
        return render_template("edit_persona.html", form=form, persona=None), 400

    persona = Persona(
        user_id=current_user.id,
        name=form.name.data.strip(),
        avatar=form.avatar.data.strip() if form.avatar.data else None,
        banner=form.banner.data.strip() if form.banner.data else None,
        bio=form.bio.data.strip() if form.bio.data else None,
        is_public=bool(form.is_public.data),
    )
    db.session.add(persona)
    db.session.commit()

    from flask import flash
    flash("Persona created.", "success")
    return redirect(url_for("persona.persona_profile", persona_id=persona.id))


@persona_bp.get("/p/<int:persona_id>")
@login_required
def persona_profile(persona_id: int):
    persona = Persona.query.get_or_404(persona_id)
    posts = (
        Post.query.filter_by(author_persona_id=persona.id)
        .order_by(Post.created_at.desc())
        .limit(50)
        .all()
    )
    is_owner = persona.user_id == current_user.id
    return render_template(
        "persona_profile.html",
        persona=persona,
        posts=posts,
        is_owner=is_owner,
    )


@persona_bp.get("/edit-persona/<int:persona_id>")
@login_required
def edit_persona(persona_id: int):
    persona = Persona.query.get_or_404(persona_id)
    if persona.user_id != current_user.id:
        abort(403)
    form = EditPersonaForm(obj=persona)
    return render_template("edit_persona.html", form=form, persona=persona)


@persona_bp.post("/edit-persona/<int:persona_id>")
@login_required
def edit_persona_post(persona_id: int):
    persona = Persona.query.get_or_404(persona_id)
    if persona.user_id != current_user.id:
        abort(403)

    form = EditPersonaForm()
    if not form.validate_on_submit():
        return render_template("edit_persona.html", form=form, persona=persona), 400

    persona.name = form.name.data.strip()
    persona.avatar = form.avatar.data.strip() if form.avatar.data else None
    persona.banner = form.banner.data.strip() if form.banner.data else None
    persona.bio = form.bio.data.strip() if form.bio.data else None
    persona.is_public = bool(form.is_public.data)
    db.session.commit()

    flash("Persona updated.", "success")
    return redirect(url_for("persona.persona_profile", persona_id=persona.id))

