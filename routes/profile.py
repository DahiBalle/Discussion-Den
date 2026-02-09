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
    from models import Post, SavedPost
    from flask import request
    
    user = User.query.filter_by(username=username).first_or_404()
    public_personas = Persona.query.filter_by(user_id=user.id, is_public=True).all()
    
    is_owner = current_user.is_authenticated and current_user.id == user.id
    view_mode = request.args.get('view', 'posts')
    
    if view_mode == 'saved' and is_owner:
        # Fetch posts saved by the user
        # We query Post joined with SavedPost to get the actual Post objects
        # ordered by when they were saved (most recent first)
        from models import SavedPost, Vote, Comment
        from .utils import get_identity
        
        posts_list = (
            db.session.query(Post)
            .join(SavedPost, Post.id == SavedPost.post_id)
            .filter(SavedPost.saved_by_user_id == user.id)
            .order_by(SavedPost.saved_at.desc())
            .limit(50) 
            .all()
        )
        
        # Enhance posts with user interaction data (votes, saves, etc.)
        # This is required for the feed-style post card to work correctly
        ident = get_identity()
        for post in posts_list:
            # Defaults
            post.user_vote = 0
            post.is_saved = True # We know it's saved because we fetched it from saved posts
            post.author_name = "Unknown"
            post.comment_count = 0
            
            # Get specific vote status
            if ident:
                if ident.is_persona and ident.persona_id:
                    vote = Vote.query.filter_by(post_id=post.id, voted_by_persona_id=ident.persona_id).first()
                else:
                    vote = Vote.query.filter_by(post_id=post.id, voted_by_user_id=ident.user_id).first()
                
                if vote:
                    post.user_vote = vote.value
            
            # Get author name
            if post.author_persona:
                post.author_name = post.author_persona.name
            elif post.author_user:
                post.author_name = post.author_user.username
                
            # Get comment count
            post.comment_count = Comment.query.filter_by(post_id=post.id).count()
            
        current_view = 'saved'
    else:
        # Default: show user's own posts
        posts_list = Post.query.filter_by(author_user_id=user.id).order_by(Post.created_at.desc()).limit(20).all()
        current_view = 'posts'

    return render_template(
        "user_profile.html",
        user=user,
        public_personas=public_personas,
        user_posts=posts_list, # Reusing variable name to minimize template changes for the loop
        is_owner=is_owner,
        current_view=current_view
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

