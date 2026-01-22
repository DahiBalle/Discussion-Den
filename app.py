from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, redirect, url_for

from extensions import csrf, db, login_manager


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

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # Blueprints
    from routes.api import api_bp
    from routes.auth import auth_bp
    from routes.feed import feed_bp
    from routes.persona import persona_bp
    from routes.post import post_bp
    from routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(persona_bp)
    app.register_blueprint(post_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return redirect(url_for("feed.feed"))

    # CLI helpers for grading/demo
    register_cli(app)

    # Template globals and filters
    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}
    
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Format datetime as time ago string."""
        if not dt:
            return 'unknown'
        delta = datetime.utcnow() - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        if minutes > 0:
            return f"{minutes}m ago"
        return "just now"

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

