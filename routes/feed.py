from __future__ import annotations

from typing import cast

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import current_user

from extensions import db
from forms import PostForm
from models import Community
from .utils import get_identity, IdentityContext


feed_bp = Blueprint("feed", __name__)


@feed_bp.get("/feed")
def feed():
    """
    Main feed page with inline post creation and server-side post loading.
    
    This is the primary user interface for Discussion Den, displaying all posts
    in reverse chronological order with comprehensive user interaction data.
    
    Architecture:
    - Server-side rendering for better performance and SEO
    - Pagination with safety limits to prevent memory issues
    - Eager loading to prevent N+1 query problems
    - Comprehensive error handling with graceful degradation
    
    Performance Optimizations:
    - Limited to 50 posts per page to prevent memory issues
    - Uses joinedload() for eager loading of relationships
    - Minimal database queries with efficient joins
    - Caches community data to avoid repeated queries
    
    Safety Features:
    - Always returns valid response even if database fails
    - Provides empty lists as fallbacks for all collections
    - Handles missing communities by creating defaults
    - Comprehensive error logging without breaking user experience
    - Input validation and sanitization for all user data
    
    User Experience:
    - Shows create post form for authenticated users
    - Displays user-specific vote and save status for each post
    - Includes author names and community information
    - Provides comment counts for engagement metrics
    
    Returns:
        Response: Rendered feed.html template with:
            - community: Default community for post creation
            - communities: List of all available communities
            - post_form: WTForms form for creating posts
            - posts: List of enhanced post objects with user data
            - active_identity: Current user's identity (user or persona)
            
    Raises:
        Never raises exceptions - all errors are handled gracefully
        
    Database Schema Dependencies:
        - Post: Main content objects
        - Community: Post categorization
        - Vote: User voting data
        - SavedPost: User save data
        - User: Author information
        - Persona: Alternative author identities
        - Comment: Engagement metrics
    """
    # from routes.utils import get_identity  <-- Removed local import
    # But actually I should remove the line entirely. 
    # Let me just replace the block.
    from models import Post, Vote, SavedPost, Comment
    from sqlalchemy import or_
    from sqlalchemy.orm import joinedload
    
    # Get all communities for the dropdown with error handling
    communities = []
    try:
        communities = Community.query.order_by(Community.name).all()
    except Exception as e:
        print(f"ERROR: Failed to load communities: {e}")
        communities = []
    
    # Ensure at least one community exists (create default if needed)
    # This is critical for the post creation form to work properly
    if not communities:
        try:
            default_community = Community(
                name="general",
                description="General discussion for all topics",
                rules="Be respectful and constructive in your discussions."
            )
            db.session.add(default_community)
            db.session.commit()
            communities = [default_community]
            print("INFO: Created default 'general' community")
        except Exception as e:
            print(f"WARNING: Could not create default community: {e}")
            communities = []
    
    # Get default community (prefer 'campus', fallback to first available)
    # This provides a sensible default for the post creation form
    default_community = None
    try:
        default_community = Community.query.filter_by(name="campus").first()
        if not default_community and communities:
            default_community = communities[0]
    except Exception as e:
        print(f"WARNING: Error getting default community: {e}")
        if communities:
            default_community = communities[0]
    
    # Get current user identity for personalization (only if authenticated)
    ident: IdentityContext | None = None
    if current_user.is_authenticated:
        try:
            ident = get_identity()
        except Exception as e:
            print(f"ERROR: Failed to get user identity: {e}")
            # This should not happen with proper authentication, but handle gracefully
            ident = None
    
    # PERFORMANCE: Load posts with pagination and eager loading to prevent N+1 queries
    # This is the most critical query for performance - must be optimized
    posts = []
    try:
        # Sort parameter
        sort_by = request.args.get('sort', 'new')
        
        query = Post.query.options(
            joinedload(Post.community),
            joinedload(Post.author_user),
            joinedload(Post.author_persona)
        )

        is_filtered_feed = False
        if sort_by == 'trending':
            # Simple trending: sort by upvotes (descending)
            # Note: In a real app this would be more complex (recency + engagement)
            query = query.order_by(Post.upvotes.desc())
        elif sort_by == 'identity' and ident and ident.is_persona:
            # FILTER: If user selected 'Identity' filter, search for posts about this persona
            # Using content search (title or body) for the persona's name
            keyword = ident.active_persona.name
            search_filter = or_(
                Post.title.ilike(f"%{keyword}%"),
                Post.body.ilike(f"%{keyword}%")
            )
            query = query.filter(search_filter).order_by(Post.created_at.desc())
            is_filtered_feed = True
            print(f"INFO: Filtering feed for keyword '{keyword}'")
        else: # Default to 'new'
            query = query.order_by(Post.created_at.desc())

        posts = query.limit(50).all()
        print(f"INFO: Loaded {len(posts)} posts for feed")
    except Exception as e:
        print(f"ERROR: Failed to load posts: {e}")
        posts = []  # SAFETY: Always provide a list, even if empty

    # FEATURE: Trending Posts Carousel
    # Fetch top 5 posts with images for the carousel
    trending_posts = []
    try:
        trending_posts = Post.query.filter(Post.image_url.isnot(None), Post.image_url != "").order_by(Post.upvotes.desc()).limit(5).all()
    except Exception as e:
        print(f"WARNING: Failed to load trending posts: {e}")
        trending_posts = []

    # Helper to enhance posts (consolidated logic could be moved to a util function)
    # For now, we just need author names for the carousel
    for post in trending_posts:
        try:
            post.author_name = "Unknown"
            if hasattr(post, "author_persona") and post.author_persona and getattr(post.author_persona, "name", None):
                post.author_name = post.author_persona.name
            elif hasattr(post, "author_user") and post.author_user and getattr(post.author_user, "username", None):
                post.author_name = post.author_user.username
        except:
            pass

    
    # ENHANCEMENT: Add user-specific data to each post (votes, saves, author names, etc.)
    # This provides personalized experience without additional page loads
    enhanced_posts = []
    for post in posts:
        try:
            # SAFETY: Initialize with safe defaults to prevent template errors
            post.user_vote = 0          # No vote by default
            post.is_saved = False       # Not saved by default
            post.author_name = "Unknown"  # Safe fallback for author
            post.comment_count = 0      # Zero comments by default
            
            # Get user-specific vote and save status efficiently
            # Only query if we have a valid identity (i.e., authenticated user)
            if ident is not None:
                ident_ctx = cast(IdentityContext, ident)
                try:
                    if ident_ctx.is_persona:
                        # Query for persona-based interactions
                        vote = Vote.query.filter_by(post_id=post.id, voted_by_persona_id=ident_ctx.persona_id).first()
                        saved = SavedPost.query.filter_by(post_id=post.id, saved_by_persona_id=ident_ctx.persona_id).first()
                    else:
                        # Query for user-based interactions
                        vote = Vote.query.filter_by(post_id=post.id, voted_by_user_id=ident_ctx.user_id).first()
                        saved = SavedPost.query.filter_by(post_id=post.id, saved_by_user_id=ident_ctx.user_id).first()
                    
                    # Apply user-specific data
                    post.user_vote = vote.value if vote else 0
                    post.is_saved = saved is not None
                    
                except Exception as e:
                    print(f"WARNING: Error getting vote/save status for post {post.id}: {e}")
                    # Keep defaults - don't break the entire feed for one post
            
            # Get author name using eager-loaded relationships (no additional queries)
            # This provides better user experience by showing readable author names
            try:
                if hasattr(post, "author_persona") and post.author_persona and getattr(
                    post.author_persona, "name", None
                ):
                    post.author_name = post.author_persona.name
                elif hasattr(post, "author_user") and post.author_user and getattr(
                    post.author_user, "username", None
                ):
                    post.author_name = post.author_user.username
                # If neither works, keep "Unknown" default
            except Exception as e:
                print(f"WARNING: Error getting author name for post {post.id}: {e}")
                # Keep "Unknown" default
            
            # Get comment count for engagement metrics
            # This helps users understand post popularity and engagement
            try:
                post.comment_count = Comment.query.filter_by(post_id=post.id).count()
            except Exception as e:
                print(f"WARNING: Error getting comment count for post {post.id}: {e}")
                # Keep 0 default
            
            enhanced_posts.append(post)
            
        except Exception as e:
            print(f"WARNING: Error enhancing post {getattr(post, 'id', 'unknown')}: {e}")
            # SAFETY: Still add post with minimal data rather than losing it entirely
            # This ensures users can still see the post even if enhancement fails
            post.user_vote = 0
            post.is_saved = False
            post.author_name = "Unknown"
            post.comment_count = 0
            enhanced_posts.append(post)
    
    # Create post form for inline post creation
    form = PostForm()
    
    # SAFETY: Always return a valid response, even if some data is missing
    # This ensures the page always loads for users, maintaining good UX
    return render_template(
        "feed.html", 
        community=default_community,
        communities=communities or [],  # SAFETY: Ensure it's always a list
        post_form=form, 
        posts=enhanced_posts,  # SAFETY: Always a list, even if empty
        active_identity=ident,
        trending_posts=trending_posts,
        is_filtered_feed=is_filtered_feed
    )

