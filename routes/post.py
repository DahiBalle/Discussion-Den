from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import CommentForm, PostForm
from models import Comment, Post
from routes.utils import get_identity


post_bp = Blueprint("post", __name__)


@post_bp.get("/post/<int:post_id>")
@login_required
def post_detail(post_id: int):
    post = Post.query.get_or_404(post_id)
    ident = get_identity()
    
    # Get vote and save status for current identity
    from models import Vote, SavedPost
    if ident.is_persona:
        vote = Vote.query.filter_by(post_id=post_id, voted_by_persona_id=ident.persona_id).first()
        saved = SavedPost.query.filter_by(post_id=post_id, saved_by_persona_id=ident.persona_id).first()
    else:
        vote = Vote.query.filter_by(post_id=post_id, voted_by_user_id=ident.user_id).first()
        saved = SavedPost.query.filter_by(post_id=post_id, saved_by_user_id=ident.user_id).first()
    
    post.user_vote = vote.value if vote else 0
    post.is_saved = saved is not None
    
    return render_template(
        "post_detail.html",
        post=post,
        comment_form=CommentForm(),
    )


@post_bp.get("/post/create")
@login_required
def create_post():
    """Show form to create a new post."""
    from models import Community
    from routes.utils import get_identity
    
    communities = Community.query.all()
    form = PostForm()
    ident = get_identity()
    return render_template(
        "create_post.html",
        form=form,
        communities=communities,
        active_identity=ident,
    )


@post_bp.post("/post/create")
@login_required
def create_post_post():
    """
    Create a post as the active identity.
    """
    form = PostForm()
    if not form.validate_on_submit():
        from models import Community
        communities = Community.query.all()
        ident = get_identity()
        flash("Please fix the post form errors.", "danger")
        return render_template(
            "create_post.html",
            form=form,
            communities=communities,
            active_identity=ident,
        ), 400

    ident = get_identity()
    post = Post(
        community_id=int(request.form.get("community_id", 1)),
        title=form.title.data.strip(),
        body=form.body.data.strip(),
        image_url=form.image_url.data.strip() if form.image_url.data else None,
        author_user_id=ident.user_id if not ident.is_persona else None,
        author_persona_id=ident.persona_id if ident.is_persona else None,
    )
    db.session.add(post)
    db.session.commit()

    flash("Posted.", "success")
    return redirect(url_for("post.post_detail", post_id=post.id))


@post_bp.post("/post/<int:post_id>/comment")
@login_required
def add_comment(post_id: int):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if not form.validate_on_submit():
        flash("Comment can't be empty.", "danger")
        return redirect(url_for("post.post_detail", post_id=post.id))

    parent_id = request.form.get("parent_comment_id")
    parent_comment_id = int(parent_id) if parent_id else None

    # Basic validation: parent must belong to the same post.
    if parent_comment_id:
        parent = Comment.query.get(parent_comment_id)
        if not parent or parent.post_id != post.id:
            abort(400)

    ident = get_identity()
    comment = Comment(
        post_id=post.id,
        body=form.body.data.strip(),
        parent_comment_id=parent_comment_id,
        author_user_id=ident.user_id if not ident.is_persona else None,
        author_persona_id=ident.persona_id if ident.is_persona else None,
    )
    db.session.add(comment)
    db.session.commit()

    flash("Comment posted.", "success")
    return redirect(url_for("post.post_detail", post_id=post.id))

