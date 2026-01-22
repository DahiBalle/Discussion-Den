from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from models import Comment, Persona, Post, SavedPost, Vote
from routes.utils import get_identity


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _post_author_payload(post: Post) -> dict:
    # Minimal payload for UI identity badges.
    if post.author_persona_id:
        persona = Persona.query.get(post.author_persona_id)
        return {
            "type": "persona",
            "id": persona.id,
            "name": persona.name,
            "avatar": persona.avatar,
        }
    return {
        "type": "user",
        "username": current_user.username if post.author_user_id == current_user.id else None,
        "id": post.author_user_id,
        "name": None,
        "avatar": None,
    }


def _post_to_card_json(post: Post) -> dict:
    ident = get_identity()

    # Saved?
    if ident.is_persona:
        saved = (
            SavedPost.query.filter_by(
                post_id=post.id, saved_by_persona_id=ident.persona_id
            ).first()
            is not None
        )
        vote = Vote.query.filter_by(post_id=post.id, voted_by_persona_id=ident.persona_id).first()
    else:
        saved = (
            SavedPost.query.filter_by(post_id=post.id, saved_by_user_id=ident.user_id).first()
            is not None
        )
        vote = Vote.query.filter_by(post_id=post.id, voted_by_user_id=ident.user_id).first()

    # Get author name
    author_name = None
    if post.author_persona_id:
        persona = Persona.query.get(post.author_persona_id)
        author_name = persona.name if persona else "Unknown"
    elif post.author_user_id:
        from models import User
        user = User.query.get(post.author_user_id)
        author_name = user.username if user else "Unknown"

    # Get community name
    community_name = None
    if post.community_id:
        from models import Community
        community = Community.query.get(post.community_id)
        community_name = community.name if community else None

    # Get comment count
    comment_count = Comment.query.filter_by(post_id=post.id).count()

    return {
        "id": post.id,
        "title": post.title,
        "body": post.body or "",
        "image_url": post.image_url,
        "created_at": post.created_at.isoformat(),
        "community_name": community_name,
        "upvotes": post.upvotes,
        "downvotes": post.downvotes,
        "is_saved": saved,
        "user_vote": vote.value if vote else 0,
        "author_name": author_name,
        "author_persona_id": post.author_persona_id,
        "author_user_id": post.author_user_id,
        "comment_count": comment_count,
    }


@api_bp.get("/me/identity")
@login_required
def me_identity():
    ident = get_identity()
    return jsonify(
        {
            "active_persona_id": ident.persona_id,
            "label": ident.label,
            "is_persona": ident.is_persona,
        }
    )


@api_bp.post("/persona/switch")
@login_required
def persona_switch():
    # Handle both JSON and form data
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json(silent=True) or {}
        persona_id = data.get("persona_id")
    else:
        persona_id = request.form.get("persona_id")
    
    if persona_id in (None, "", 0, "0", "null"):
        session["active_persona_id"] = None
        return jsonify({"success": True, "persona_id": None})

    try:
        persona_id_int = int(persona_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid persona ID."}), 400

    persona = Persona.query.get(persona_id_int)
    if not persona or persona.user_id != current_user.id:
        return jsonify({"success": False, "error": "Invalid persona."}), 403

    session["active_persona_id"] = persona.id
    return jsonify({"success": True, "persona_id": persona.id})


@api_bp.get("/feed")
@login_required
def feed_json():
    """
    Feed endpoint for infinite scroll.

    Current behavior: a simple global community feed ordered by recency.
    Identity only affects *interactions* (vote/save) and posting identity,
    not the post selection logic.
    """
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page_size = min(int(request.args.get("page_size", 10)), 25)
    offset = max(page - 1, 0) * page_size

    posts = (
        Post.query.order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size + 1)
        .all()
    )
    has_more = len(posts) > page_size
    posts = posts[:page_size]

    return jsonify(
        {
            "success": True,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
            "posts": [_post_to_card_json(p) for p in posts],
        }
    )


@api_bp.post("/post/<int:post_id>/vote")
@login_required
def vote(post_id: int):
    data = request.get_json(silent=True) or {}
    try:
        value = int(data.get("vote", 0))
    except (ValueError, TypeError):
        value = 0
    if value not in (-1, 0, 1):
        return jsonify({"success": False, "error": "Invalid vote value."}), 400

    post = Post.query.get_or_404(post_id)
    ident = get_identity()

    if ident.is_persona:
        existing = Vote.query.filter_by(post_id=post_id, voted_by_persona_id=ident.persona_id).first()
    else:
        existing = Vote.query.filter_by(post_id=post_id, voted_by_user_id=ident.user_id).first()

    # Remove existing vote impact
    if existing:
        if existing.value == 1:
            post.upvotes = max(post.upvotes - 1, 0)
        elif existing.value == -1:
            post.downvotes = max(post.downvotes - 1, 0)

    if value == 0:
        if existing:
            db.session.delete(existing)
        db.session.commit()
        return jsonify({"success": True, "upvotes": post.upvotes, "downvotes": post.downvotes, "vote": 0})

    if existing:
        existing.value = value
    else:
        existing = Vote(
            post_id=post_id,
            voted_by_persona_id=ident.persona_id if ident.is_persona else None,
            voted_by_user_id=ident.user_id if not ident.is_persona else None,
            value=value,
        )
        db.session.add(existing)

    if value == 1:
        post.upvotes += 1
    else:
        post.downvotes += 1

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "upvotes": post.upvotes,
            "downvotes": post.downvotes,
            "vote": value,
            "score": post.upvotes - post.downvotes,
        }
    )


@api_bp.post("/post/<int:post_id>/save")
@login_required
def save(post_id: int):
    data = request.get_json(silent=True) or {}
    save_value = bool(data.get("save", True))

    Post.query.get_or_404(post_id)
    ident = get_identity()

    if ident.is_persona:
        existing = SavedPost.query.filter_by(post_id=post_id, saved_by_persona_id=ident.persona_id).first()
    else:
        existing = SavedPost.query.filter_by(post_id=post_id, saved_by_user_id=ident.user_id).first()

    if save_value:
        if not existing:
            sp = SavedPost(
                post_id=post_id,
                saved_by_persona_id=ident.persona_id if ident.is_persona else None,
                saved_by_user_id=ident.user_id if not ident.is_persona else None,
            )
            db.session.add(sp)
        db.session.commit()
        return jsonify({"success": True, "is_saved": True})

    # unsave
    if existing:
        db.session.delete(existing)
        db.session.commit()
    return jsonify({"success": True, "is_saved": False})


@api_bp.post("/post/<int:post_id>/comment")
@login_required
def add_comment_api(post_id: int):
    """API endpoint for adding comments via AJAX."""
    data = request.get_json(silent=True) or {}
    body = data.get("body", "").strip()
    parent_comment_id = data.get("parent_comment_id")
    
    if not body:
        return jsonify({"success": False, "error": "Comment body is required."}), 400
    
    post = Post.query.get_or_404(post_id)
    
    if parent_comment_id:
        parent = Comment.query.get(parent_comment_id)
        if not parent or parent.post_id != post.id:
            return jsonify({"success": False, "error": "Invalid parent comment."}), 400
    
    ident = get_identity()
    comment = Comment(
        post_id=post.id,
        body=body,
        parent_comment_id=int(parent_comment_id) if parent_comment_id else None,
        author_user_id=ident.user_id if not ident.is_persona else None,
        author_persona_id=ident.persona_id if ident.is_persona else None,
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({"success": True, "comment_id": comment.id})


@api_bp.get("/post/<int:post_id>/comments")
@login_required
def comments(post_id: int):
    Post.query.get_or_404(post_id)
    all_comments = (
        Comment.query.filter_by(post_id=post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    personas = {p.id: p for p in Persona.query.filter(Persona.id.in_([c.author_persona_id for c in all_comments if c.author_persona_id])).all()}  # noqa: E501

    def to_json(c: Comment) -> dict:
        author = None
        if c.author_persona_id:
            p = personas.get(c.author_persona_id)
            author = {"type": "persona", "id": p.id, "name": p.name, "avatar": p.avatar}
        else:
            author = {"type": "user", "id": c.author_user_id}
        return {
            "id": c.id,
            "body": c.body,
            "created_at": c.created_at.isoformat(),
            "post_id": c.post_id,
            "parent_comment_id": c.parent_comment_id,
            "author": author,
        }

    return jsonify({"ok": True, "comments": [to_json(c) for c in all_comments]})

