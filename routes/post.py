from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
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
    Handles both regular form submissions and AJAX requests from the feed page.
    
    SAFETY: Comprehensive error handling and validation.
    """
    form = PostForm()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not form.validate_on_submit():
        from models import Community
        communities = Community.query.all()
        ident = get_identity()
        flash("Please fix the post form errors.", "danger")
        
        if is_ajax:
            # Return JSON error response for AJAX requests
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors
            return jsonify({
                "success": False,
                "errors": errors,
                "message": "Please fix the form errors."
            }), 400
        else:
            # Return regular template response for non-AJAX requests
            return render_template(
                "create_post.html",
                form=form,
                communities=communities,
                active_identity=ident,
            ), 400

    ident = get_identity()
    
    # SAFETY: Validate community_id exists
    community_id = request.form.get("community_id", 1)
    try:
        community_id = int(community_id)
        from models import Community
        if not Community.query.get(community_id):
            raise ValueError("Invalid community")
    except (ValueError, TypeError):
        error_msg = "Invalid community selected."
        if is_ajax:
            return jsonify({"success": False, "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("post.create_post"))
    
    try:
        post = Post(
            community_id=community_id,
            title=form.title.data.strip(),
            body=form.body.data.strip(),
            image_url=form.image_url.data.strip() if form.image_url.data else None,
            author_user_id=ident.user_id if not ident.is_persona else None,
            author_persona_id=ident.persona_id if ident.is_persona else None,
        )
        db.session.add(post)
        db.session.commit()

        flash("Posted.", "success")
        
        if is_ajax:
            # Return JSON success response for AJAX requests
            return jsonify({
                "success": True,
                "message": "Post created successfully!",
                "post_id": post.id,
                "redirect_url": url_for("post.post_detail", post_id=post.id)
            })
        else:
            # Return regular redirect for non-AJAX requests
            return redirect(url_for("post.post_detail", post_id=post.id))
            
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to create post: {e}")
        
        error_msg = "There was an error creating your post. Please try again."
        if is_ajax:
            return jsonify({"success": False, "message": error_msg}), 500
        else:
            flash(error_msg, "danger")
            return redirect(url_for("post.create_post"))


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

