from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id: str):
    """
    Callback function for Flask-Login to load a user from the session.

    Args:
        user_id (str): The user ID stored in the session.

    Returns:
        User: The User object if found, otherwise None.
    """
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """
    Represents a registered user of the application.

    Users can create Personas, join Communities, make Posts, and Comment.
    This model handles authentication via Flask-Login (UserMixin).
    """
    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Authentication & Profile Fields
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional Profile Details
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True) # URL to avatar image
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    # A User can have multiple Personas (aliases).
    # cascade="all, delete-orphan": If User is deleted, delete all their Personas.
    personas: Mapped[list["Persona"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Persona(db.Model):
    """
    Represents an alias (Persona) created by a User.

    A User can switch between different Personas to post with different identities
    (e.g., "Professional Self" vs "Gamer Self").
    """
    __tablename__ = "personas"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign Key: Link to the parent User
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Persona Profile Details
    name: Mapped[str] = mapped_column(String(48), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Visibility: intended for future features (e.g., hidden personas)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="personas")

    def __repr__(self) -> str:
        return f"<Persona {self.id}:{self.name}>"


class Community(db.Model):
    """
    Represents a topic-specific community (like a Subreddit).
    Users post content into specific communities.
    """
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    # A Community contains multiple Posts.
    posts: Mapped[list["Post"]] = relationship(back_populates="community")

    def __repr__(self) -> str:
        return f"<Community {self.name}>"


class Post(db.Model):
    """
    Represents a user-submitted piece of content within a Community.

    A Post must be authored by EITHER a User OR a Persona, but not both at the same time.
    This exclusivity is enforced via a CheckConstraint.
    """
    __tablename__ = "posts"

    # Core Content
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Voting Metrics (denormalized counts for performance)
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Foreign Keys
    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    
    # Author Reference (Mutually Exclusive)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )

    # Relationships
    community: Mapped[Community] = relationship(back_populates="posts")
    author_user: Mapped["User | None"] = relationship("User", foreign_keys=[author_user_id])
    author_persona: Mapped["Persona | None"] = relationship("Persona", foreign_keys=[author_persona_id])
    
    # Comments on this post
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    # Cascading deletes for Votes and Saves
    votes: Mapped[list["Vote"]] = relationship("Vote", cascade="all, delete-orphan")
    saved_posts: Mapped[list["SavedPost"]] = relationship("SavedPost", cascade="all, delete-orphan")

    __table_args__ = (
        # Constraint: Ensure a post has exactly one author source (User OR Persona)
        CheckConstraint(
            "(author_user_id IS NOT NULL AND author_persona_id IS NULL) OR "
            "(author_user_id IS NULL AND author_persona_id IS NOT NULL)",
            name="ck_post_exactly_one_author_identity",
        ),
        # Index for efficient sorting by date
        Index("ix_posts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Post {self.id}:{self.title[:24]!r}>"


class Comment(db.Model):
    """
    Represents a comment on a Post.
    
    Can be a top-level comment or a reply to another comment (nested).
    Like Posts, Comments must be authored by either a User or a Persona.
    """
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    
    # Author Reference (Mutually Exclusive)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )

    # Self-referencing FK for threaded comments (replies)
    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id"), nullable=True
    )

    # Relationships
    post: Mapped[Post] = relationship(back_populates="comments")
    # 'children' allows accessing replies to this comment
    parent: Mapped["Comment | None"] = relationship(remote_side="Comment.id", backref="children")

    __table_args__ = (
        # Constraint: Ensure a comment has exactly one author source
        CheckConstraint(
            "(author_user_id IS NOT NULL AND author_persona_id IS NULL) OR "
            "(author_user_id IS NULL AND author_persona_id IS NOT NULL)",
            name="ck_comment_exactly_one_author_identity",
        ),
        # Index for fetching comments for a specific post quickly
        Index("ix_comments_post_id_created_at", "post_id", "created_at"),
    )


class SavedPost(db.Model):
    """
    Represents a 'Save' action where a User or Persona saves a post for later logic.
    """
    __tablename__ = "saved_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

    # Saved By Identity (Mutually Exclusive)
    saved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    saved_by_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(saved_by_user_id IS NOT NULL AND saved_by_persona_id IS NULL) OR "
            "(saved_by_user_id IS NULL AND saved_by_persona_id IS NOT NULL)",
            name="ck_saved_exactly_one_identity",
        ),
        # Partial Unique Indexes: Prevent duplicate saves by the same identity
        # Postgres-specific optimizations for cleaner constraints
        Index(
            "uq_saved_user_per_post",
            "post_id",
            "saved_by_user_id",
            unique=True,
            postgresql_where=(saved_by_persona_id.is_(None)),
        ),
        Index(
            "uq_saved_persona_per_post",
            "post_id",
            "saved_by_persona_id",
            unique=True,
            postgresql_where=(saved_by_user_id.is_(None)),
        ),
    )


class Vote(db.Model):
    """
    Represents an Upvote or Downvote on a Post. 
    Tracks who voted to prevent duplicate voting.
    """
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

    # Voted By Identity (Mutually Exclusive)
    voted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    voted_by_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )
    
    # Value: +1 for Upvote, -1 for Downvote
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1

    __table_args__ = (
        # Validate that vote is either +1 or -1
        CheckConstraint("value IN (-1, 1)", name="ck_vote_value"),
        # Ensure exactly one voter identity is set
        CheckConstraint(
            "(voted_by_user_id IS NOT NULL AND voted_by_persona_id IS NULL) OR "
            "(voted_by_user_id IS NULL AND voted_by_persona_id IS NOT NULL)",
            name="ck_vote_exactly_one_identity",
        ),
        # Unique constraints: A user/persona can only vote once per post.
        # If they change vote, we update the existing row rather than inserting a new one.
        Index(
            "uq_vote_user_per_post",
            "post_id",
            "voted_by_user_id",
            unique=True,
            postgresql_where=(voted_by_persona_id.is_(None)),
        ),
        Index(
            "uq_vote_persona_per_post",
            "post_id",
            "voted_by_persona_id",
            unique=True,
            postgresql_where=(voted_by_user_id.is_(None)),
        ),
        Index("ix_votes_post_id", "post_id"),
    )