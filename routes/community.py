from __future__ import annotations

from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import CommunityForm
from models import Community, Post
from routes.utils import get_identity


community_bp = Blueprint("community", __name__)


@community_bp.get("/community/<string:community_name>")
def community_page(community_name: str):
    """
    Display posts for a specific community.
    
    Safety: Uses existing Post model and templates.
    No database changes required.
    """
    # Validate community exists
    community = Community.query.filter_by(name=community_name).first()
    if not community:
        abort(404)
    
    # Get identity for template context (only for authenticated users)
    ident = None
    if current_user.is_authenticated:
        ident = get_identity()
    
    # Get recent posts for this community (limit for performance)
    posts = (
        Post.query
        .filter_by(community_id=community.id)
        .order_by(Post.created_at.desc())
        .limit(20)
        .all()
    )
    
    # Add vote/save status for each post (reusing existing logic)
    from models import Vote, SavedPost
    for post in posts:
        # defaults for anonymous users
        post.user_vote = 0
        post.is_saved = False

        if ident:
            if ident.is_persona:
                vote = Vote.query.filter_by(post_id=post.id, voted_by_persona_id=ident.persona_id).first()
                saved = SavedPost.query.filter_by(post_id=post.id, saved_by_persona_id=ident.persona_id).first()
            else:
                vote = Vote.query.filter_by(post_id=post.id, voted_by_user_id=ident.user_id).first()
                saved = SavedPost.query.filter_by(post_id=post.id, saved_by_user_id=ident.user_id).first()
            
            post.user_vote = vote.value if vote else 0
            post.is_saved = saved is not None
        
        # Add author name for display (reusing API logic)
        if post.author_persona_id:
            from models import Persona
            persona = Persona.query.get(post.author_persona_id)
            post.author_name = persona.name if persona else "Unknown"
        elif post.author_user_id:
            from models import User
            user = User.query.get(post.author_user_id)
            post.author_name = user.username if user else "Unknown"
        else:
            post.author_name = "Unknown"
    
    return render_template(
        "community_page.html",
        community=community,
        posts=posts,
        active_identity=ident,
    )


@community_bp.get("/communities")
def communities_list():
    """
    List all available communities.
    
    Safety: Read-only operation, no modifications.
    """
    communities = Community.query.order_by(Community.name.asc()).all()
    ident = get_identity() if current_user.is_authenticated else None
    
    # Add post count for each community
    for community in communities:
        community.post_count = Post.query.filter_by(community_id=community.id).count()
    
    return render_template(
        "communities_list.html",
        communities=communities,
        active_identity=ident,
    )


@community_bp.get("/community/create")
@login_required
def create_community():
    """
    Show form to create a new community.
    
    Safety: Follows existing create_post pattern.
    """
    form = CommunityForm()
    ident = get_identity()
    return render_template(
        "create_community.html",
        form=form,
        active_identity=ident,
    )


@community_bp.post("/community/create")
@login_required
def create_community_post():
    """
    Create a new community with enhanced validation and error handling.
    
    Safety Features:
    - Comprehensive input validation and sanitization
    - Duplicate name detection with race condition protection
    - Graceful error handling with user-friendly messages
    - Defensive programming against malformed inputs
    - Transaction rollback on any failure
    
    Limitations:
    - No ownership tracking (Community model lacks owner field)
    - Would require database schema changes to add ownership
    """
    form = CommunityForm()
    if not form.validate_on_submit():
        ident = get_identity()
        flash("Please fix the form errors.", "danger")
        return render_template(
            "create_community.html",
            form=form,
            active_identity=ident,
        ), 400

    # Enhanced validation: Clean and validate community name
    try:
        community_name = form.name.data.strip().lower() if form.name.data else ""
    except (AttributeError, TypeError):
        community_name = ""
    
    # Comprehensive name validation
    if not community_name:
        flash("Community name is required.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 400
    
    if len(community_name) < 2:
        flash("Community name must be at least 2 characters long.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 400
    
    if len(community_name) > 64:
        flash("Community name must be 64 characters or less.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 400
    
    # Enhanced: Check for invalid characters
    import re
    if not re.match(r'^[a-z0-9_]+$', community_name):
        flash("Community name can only contain lowercase letters, numbers, and underscores.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 400

    # Safety: Check for existing community name with better error handling
    try:
        existing = Community.query.filter_by(name=community_name).first()
        if existing:
            flash(f"Community 'r/{community_name}' already exists.", "danger")
            ident = get_identity()
            return render_template("create_community.html", form=form, active_identity=ident), 400
    except Exception as e:
        print(f"ERROR: Database error checking existing community: {e}")
        flash("Database error occurred. Please try again.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 500

    # Enhanced: Validate and sanitize description and rules
    try:
        description = form.description.data.strip() if form.description.data else None
        rules = form.rules.data.strip() if form.rules.data else None
        
        # Length validation for description and rules
        if description and len(description) > 1000:
            flash("Description must be 1000 characters or less.", "danger")
            ident = get_identity()
            return render_template("create_community.html", form=form, active_identity=ident), 400
        
        if rules and len(rules) > 2000:
            flash("Rules must be 2000 characters or less.", "danger")
            ident = get_identity()
            return render_template("create_community.html", form=form, active_identity=ident), 400
            
    except (AttributeError, TypeError):
        description = None
        rules = None

    try:
        # Create community with validated data
        community = Community(
            name=community_name,
            description=description,
            rules=rules,
        )
        db.session.add(community)
        db.session.commit()

        flash(f"Community 'r/{community_name}' created successfully!", "success")
        return redirect(url_for("community.community_page", community_name=community_name))

    except IntegrityError as e:
        # Safety: Handle race condition where name was taken between check and insert
        db.session.rollback()
        print(f"WARNING: IntegrityError creating community '{community_name}': {e}")
        flash(f"Community 'r/{community_name}' already exists.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 400
        
    except Exception as e:
        # Safety: Handle any other database errors gracefully
        db.session.rollback()
        print(f"ERROR: Unexpected error creating community '{community_name}': {e}")
        flash("An error occurred while creating the community. Please try again.", "danger")
        ident = get_identity()
        return render_template("create_community.html", form=form, active_identity=ident), 500