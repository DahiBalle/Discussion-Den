from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, redirect, url_for

from extensions import csrf, db, login_manager, oauth, limiter, mail


def create_app() -> Flask:
    """
    Application factory.

    Why: keeps initialization clean, testable, and avoids circular imports between
    models, forms, and blueprints.
    """
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-not-for-production")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required (PostgreSQL). Set it in your environment or .env."
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Mail Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
    
    mail.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # Initialize Google OAuth (OPTIONAL - graceful if not configured)
    oauth.init_app(app)
    try:
        google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        
        # Enhanced validation: Check for placeholder values and empty strings
        def is_valid_credential(credential):
            """Check if credential is valid (not None, empty, or placeholder)"""
            if not credential or credential.strip() == "":
                return False
            # Check for common placeholder patterns
            placeholder_patterns = [
                "your_google_client_id_here",
                "your_google_client_secret_here", 
                "your_client_id",
                "your_client_secret",
                "replace_with_your",
                "add_your_client_id",
                "add_your_client_secret"
            ]
            return credential.lower() not in placeholder_patterns
        
        if is_valid_credential(google_client_id) and is_valid_credential(google_client_secret):
            oauth.register(
                name='google',
                client_id=google_client_id,
                client_secret=google_client_secret,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            print("INFO: Google OAuth configured successfully")
            print(f"DEBUG: OAuth registry contains: {list(oauth._registry.keys()) if hasattr(oauth, '_registry') else 'No registry'}")
            print(f"DEBUG: hasattr(oauth, 'google'): {hasattr(oauth, 'google')}")
        else:
            print("INFO: Google OAuth not configured (missing or invalid GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)")
            print("HINT: Update your .env file with real Google OAuth credentials from Google Cloud Console")
            print(f"DEBUG: Client ID valid: {is_valid_credential(google_client_id)}")
            print(f"DEBUG: Client Secret valid: {is_valid_credential(google_client_secret)}")
    except Exception as e:
        print(f"WARNING: Google OAuth configuration failed: {e}")
        # Continue without Google OAuth - existing auth still works

    # Blueprints
    from routes.api import api_bp
    from routes.auth import auth_bp
    from routes.community import community_bp
    from routes.feed import feed_bp
    from routes.persona import persona_bp
    from routes.post import post_bp
    from routes.profile import profile_bp
    from routes.search import search_bp
    from routes.pages import pages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(persona_bp)
    app.register_blueprint(post_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(pages_bp)

    @app.route("/")
    def index():
        return redirect(url_for("feed.feed"))

    # CLI helpers for grading/demo
    register_cli(app)

    # Template globals and filters
    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}
    
    @app.context_processor
    def inject_sidebar_data():
        """
        Inject trending posts and recent communities for offcanvas sidebar.
        Also inject show_welcome_card: hide welcome card if user has created at least one post.
        """
        from flask_login import current_user
        from sqlalchemy import or_
        from models import Post, Community

        # Show welcome card only when user has never created a post (as user or any persona)
        show_welcome_card = True
        if current_user.is_authenticated:
            try:
                persona_ids = [p.id for p in current_user.personas]
                if persona_ids:
                    post_count = Post.query.filter(
                        or_(
                            Post.author_user_id == current_user.id,
                            Post.author_persona_id.in_(persona_ids),
                        )
                    ).count()
                else:
                    post_count = Post.query.filter(
                        Post.author_user_id == current_user.id
                    ).count()
                show_welcome_card = post_count == 0
            except Exception:
                show_welcome_card = True

        # Trending posts: highest upvotes, limit 5 for performance
        trending_posts = []
        try:
            trending_posts = (
                Post.query
                .filter(Post.upvotes > 0)  # Only posts with upvotes
                .order_by(Post.upvotes.desc())
                .limit(5)
                .all()
            )
        except Exception:
            trending_posts = []

        # Recent communities: newest first, limit 5 for performance
        recent_communities = []
        try:
            recent_communities = (
                Community.query
                .order_by(Community.created_at.desc())
                .limit(5)
                .all()
            )
        except Exception:
            recent_communities = []

        return {
            "trending_posts": trending_posts,
            "recent_communities": recent_communities,
            "show_welcome_card": show_welcome_card,
        }
    
    @app.context_processor
    def inject_oauth_status():
        return {
            "google_oauth_configured": (
                hasattr(oauth, "_registry") and "google" in oauth._registry
        )
    }

    
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """
        Format datetime as time ago string with improved accuracy and safety.
        
        This filter converts datetime objects to human-readable relative time strings
        (e.g., "2h ago", "3d ago"). It's designed to be safe and never break template
        rendering, even with malformed or missing datetime values.
        
        Technical Details:
        - Assumes all naive datetime objects are stored in UTC (safe assumption for this app)
        - Uses datetime.utcnow() for consistent timezone handling
        - Handles edge cases like future dates (clock skew) gracefully
        - Provides consistent time ranges matching client-side JavaScript logic
        
        Args:
            dt (datetime): The datetime object to format. Can be None or invalid.
            
        Returns:
            str: Human-readable time string like "2h ago", "just now", or "recently"
                 Never returns None or raises exceptions.
                 
        Safety Features:
        - Never raises exceptions that could break template rendering
        - Validates input type and handles None/invalid values
        - Provides fallback values for all error conditions
        - Logs errors for debugging without breaking user experience
        - Handles future dates gracefully (returns "just now")
        
        Examples:
            >>> timeago_filter(datetime(2023, 1, 1, 12, 0))  # 2 hours ago
            "2h ago"
            >>> timeago_filter(None)
            "unknown"
            >>> timeago_filter("invalid")
            "unknown"
        """
        try:
            # Input validation - ensure we have a valid datetime object
            if not dt:
                return 'unknown'
            
            # Type safety - validate datetime object type
            if not isinstance(dt, datetime):
                return 'unknown'
            
            # All database timestamps are stored as UTC via datetime.utcnow()
            # For naive datetimes, we can safely assume they're UTC since that's how they're stored
            now = datetime.utcnow()
            
            # Calculate delta - both dt and now are naive UTC datetimes
            delta = now - dt
            
            # Handle future dates gracefully (clock skew protection)
            # This can happen with server time differences or client clock issues
            if delta.total_seconds() < 0:
                return 'just now'
            
            # Convert to consistent integer values for reliable calculations
            total_seconds = int(delta.total_seconds())
            days = delta.days
            
            # Time range calculations - consistent with client-side JavaScript
            # Using standard time units for better user understanding
            if days > 365:
                years = days // 365
                return f"{years}y ago"
            elif days > 30:
                months = days // 30
                return f"{months}mo ago"
            elif days > 7:
                weeks = days // 7
                return f"{weeks}w ago"
            elif days > 0:
                return f"{days}d ago"
            
            # Sub-day calculations
            hours = total_seconds // 3600
            if hours > 0:
                return f"{hours}h ago"
            
            minutes = total_seconds // 60
            if minutes > 0:
                return f"{minutes}m ago"
            
            # Very recent posts
            return "just now"
            
        except Exception as e:
            # CRITICAL SAFETY: Never let timeago filter break template rendering
            # This is the most important safety feature - templates must always render
            # Log the error for debugging but return a safe fallback value
            print(f"WARNING: timeago filter error: {e}, dt={dt}")
            return 'recently'  # Safe fallback that's always user-friendly

    return app


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        from models import User, Community, Post, Persona, Comment   # noqa: WPS433 (import inside command)
        print("DB URI:", app.config["SQLALCHEMY_DATABASE_URI"])
        with app.app_context():
            db.create_all()
            # Ensure at least one community exists for the feed UX.
            if not Community.query.first():
                db.session.add(
                    Community(
                        name="campus",
                        description="Campus-wide discussion and announcements.",
                        rules="Be kind. No doxxing. Keep it constructive.",
                    )
                )
                db.session.commit()
            print("Database initialized.")

    @app.cli.command("seed")
    def seed():
        """Seed example content for quick demo."""
        from models import Comment, Community, Persona, Post, User  # noqa: WPS433
        from werkzeug.security import generate_password_hash  # noqa: WPS433

        with app.app_context():
            db.create_all()

            community = Community.query.filter_by(name="campus").first()
            if not community:
                community = Community(
                    name="campus",
                    description="Campus-wide discussion and announcements.",
                    rules="Be kind. No doxxing. Keep it constructive.",
                )
                db.session.add(community)
                db.session.commit()

            if User.query.filter_by(username="student").first():
                print("Seed already applied.")
                return

            user = User(
                username="student",
                email="student@example.com",
                password_hash=generate_password_hash("password"),
                bio="Computer science student. Loves clean UI and strong coffee.",
            )
            db.session.add(user)
            db.session.flush()

            persona = Persona(
                user_id=user.id,
                name="Lab Partner",
                bio="Here for group projects and study tips.",
                is_public=True,
            )
            db.session.add(persona)
            db.session.flush()

            p1 = Post(
                community_id=community.id,
                title="Best quiet study spots on campus?",
                body="Drop your go-to spots. Bonus points for outlets and good lighting.",
                author_user_id=user.id,
            )
            p2 = Post(
                community_id=community.id,
                title="Reminder: Lab report formatting",
                body="If you’re submitting today, double-check your figures and captions.",
                author_persona_id=persona.id,
            )
            db.session.add_all([p1, p2])
            db.session.flush()

            c1 = Comment(
                post_id=p1.id,
                body="Library 3rd floor is underrated. Go early.",
                author_persona_id=persona.id,
            )
            c2 = Comment(
                post_id=p1.id,
                body="Seconding this—also the engineering building lobby.",
                author_user_id=user.id,
                parent_comment_id=None,
            )
            db.session.add_all([c1, c2])
            db.session.commit()
            print("Seed complete. Login: student / password")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)