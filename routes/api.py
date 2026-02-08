from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db, limiter
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
    """Convert Post object to JSON for API responses.
    
    CRITICAL: This function must never raise exceptions that break the API.
    All fields must have safe fallbacks.
    """
    try:
        ident = get_identity()

        # Saved status - with safe fallbacks
        saved = False
        vote = None
        try:
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
        except Exception as e:
            print(f"WARNING: Error getting vote/save status for post {post.id}: {e}")
            saved = False
            vote = None

        # Get author name - with safe fallbacks
        author_name = "Unknown"
        try:
            if post.author_persona_id:
                persona = Persona.query.get(post.author_persona_id)
                author_name = persona.name if persona else "Unknown Persona"
            elif post.author_user_id:
                from models import User
                user = User.query.get(post.author_user_id)
                author_name = user.username if user else "Unknown User"
        except Exception as e:
            print(f"WARNING: Error getting author name for post {post.id}: {e}")
            author_name = "Unknown"

        # Get community name - with safe fallbacks
        community_name = None
        try:
            if post.community_id:
                from models import Community
                community = Community.query.get(post.community_id)
                community_name = community.name if community else None
        except Exception as e:
            print(f"WARNING: Error getting community name for post {post.id}: {e}")
            community_name = None

        # Get comment count - with safe fallbacks
        comment_count = 0
        try:
            comment_count = Comment.query.filter_by(post_id=post.id).count()
        except Exception as e:
            print(f"WARNING: Error getting comment count for post {post.id}: {e}")
            comment_count = 0

        # Safe timestamp formatting
        created_at_iso = None
        try:
            created_at_iso = post.created_at.isoformat() if post.created_at else datetime.utcnow().isoformat()
        except Exception as e:
            print(f"WARNING: Error formatting timestamp for post {post.id}: {e}")
            created_at_iso = datetime.utcnow().isoformat()

        return {
            "id": post.id or 0,
            "title": post.title or "Untitled",
            "body": post.body or "",
            "image_url": post.image_url or None,
            "created_at": created_at_iso,
            "community_name": community_name,
            "upvotes": post.upvotes or 0,
            "downvotes": post.downvotes or 0,
            "is_saved": saved,
            "user_vote": vote.value if vote else 0,
            "author_name": author_name,
            "author_persona_id": post.author_persona_id,
            "author_user_id": post.author_user_id,
            "comment_count": comment_count,
        }
        
    except Exception as e:
        # CRITICAL: Never let post serialization break the entire API
        print(f"CRITICAL ERROR: Failed to serialize post {getattr(post, 'id', 'unknown')}: {e}")
        return {
            "id": getattr(post, 'id', 0),
            "title": "Error loading post",
            "body": "There was an error loading this post.",
            "image_url": None,
            "created_at": datetime.utcnow().isoformat(),
            "community_name": None,
            "upvotes": 0,
            "downvotes": 0,
            "is_saved": False,
            "user_vote": 0,
            "author_name": "System",
            "author_persona_id": None,
            "author_user_id": None,
            "comment_count": 0,
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
@limiter.limit("20 per minute")
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
    
    New: Optional community filtering via ?community=<name> parameter.
    """
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page_size = min(int(request.args.get("page_size", 10)), 25)
    offset = max(page - 1, 0) * page_size

    # Optional community filtering (safe extension)
    community_name = request.args.get("community")
    query = Post.query
    
    if community_name:
        # Filter by community if specified
        from models import Community
        community = Community.query.filter_by(name=community_name).first()
        if community:
            query = query.filter_by(community_id=community.id)
        else:
            # Invalid community name - return empty results safely
            return jsonify({
                "success": True,
                "page": page,
                "page_size": page_size,
                "has_more": False,
                "posts": [],
                "error": "Community not found"
            })

    posts = (
        query.order_by(Post.created_at.desc())
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
@limiter.limit("30 per minute")
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
        # Re-query to handle race: another request may have created a vote already
        if ident.is_persona:
            existing = Vote.query.filter_by(post_id=post_id, voted_by_persona_id=ident.persona_id).first()
        else:
            existing = Vote.query.filter_by(post_id=post_id, voted_by_user_id=ident.user_id).first()
        if existing:
            existing.value = value
            db.session.commit()
            post = Post.query.get_or_404(post_id)
            return jsonify(
                {
                    "success": True,
                    "upvotes": post.upvotes,
                    "downvotes": post.downvotes,
                    "vote": value,
                    "score": post.upvotes - post.downvotes,
                }
            )
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
@limiter.limit("60 per minute")
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
@limiter.limit("10 per minute")
def add_comment_api(post_id: int):
    """
    API endpoint for adding comments via AJAX.
    
    SAFETY: Validates comment depth to prevent infinite nesting.
    """
    data = request.get_json(silent=True) or {}
    body = data.get("body", "").strip()
    parent_comment_id = data.get("parent_comment_id")
    
    if not body:
        return jsonify({"success": False, "error": "Comment body is required."}), 400
    
    post = Post.query.get_or_404(post_id)
    
    # SAFETY: Validate parent comment and check nesting depth
    if parent_comment_id:
        try:
            parent_comment_id = int(parent_comment_id)
            parent = Comment.query.get(parent_comment_id)
            if not parent or parent.post_id != post.id:
                return jsonify({"success": False, "error": "Invalid parent comment."}), 400
            
            # SAFETY: Check nesting depth to prevent excessive nesting
            depth = 0
            current = parent
            while current and current.parent_comment_id and depth < 10:  # Safety limit
                current = Comment.query.get(current.parent_comment_id)
                depth += 1
            
            if depth >= 3:  # Max depth of 3 levels
                return jsonify({
                    "success": False, 
                    "error": "Maximum reply depth reached. Please reply to a higher-level comment."
                }), 400
                
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid parent comment ID."}), 400
    
    ident = get_identity()
    
    try:
        comment = Comment(
            post_id=post.id,
            body=body,
            parent_comment_id=parent_comment_id,
            author_user_id=ident.user_id if not ident.is_persona else None,
            author_persona_id=ident.persona_id if ident.is_persona else None,
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({"success": True, "comment_id": comment.id})
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to create comment: {e}")
        return jsonify({
            "success": False, 
            "error": "Failed to post comment. Please try again."
        }), 500


@api_bp.get("/post/<int:post_id>/comments")
def comments(post_id: int):
    """
    Public comments endpoint.

    - Read-only: anyone (authenticated or not) can view comments.
    - Still validates post existence.
    """
    Post.query.get_or_404(post_id)
    all_comments = (
        Comment.query.filter_by(post_id=post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    personas = {
        p.id: p
        for p in Persona.query.filter(
            Persona.id.in_(
                [c.author_persona_id for c in all_comments if c.author_persona_id]
            )
        ).all()
    }

    def to_json(c: Comment) -> dict:
        if c.author_persona_id:
            p = personas.get(c.author_persona_id)
            author = {
                "type": "persona",
                "id": p.id if p else None,
                "name": p.name if p else "Unknown",
                "avatar": p.avatar if p else None,
            }
        else:
            # Get username for user-type authors
            from models import User

            user = User.query.get(c.author_user_id) if c.author_user_id else None
            author = {
                "type": "user",
                "id": c.author_user_id,
                "username": user.username if user else "Unknown",
            }
        return {
            "id": c.id,
            "body": c.body,
            "created_at": c.created_at.isoformat(),
            "post_id": c.post_id,
            "parent_comment_id": c.parent_comment_id,
            "author": author,
        }

    return jsonify({"success": True, "comments": [to_json(c) for c in all_comments]})

