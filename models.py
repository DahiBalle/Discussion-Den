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
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    personas: Mapped[list["Persona"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Persona(db.Model):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(48), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped[User] = relationship(back_populates="personas")

    def __repr__(self) -> str:
        return f"<Persona {self.id}:{self.name}>"


class Community(db.Model):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    posts: Mapped[list["Post"]] = relationship(back_populates="community")

    def __repr__(self) -> str:
        return f"<Community {self.name}>"


class Post(db.Model):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    community_id: Mapped[int] = mapped_column(ForeignKey("communities.id"), nullable=False)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )

    community: Mapped[Community] = relationship(back_populates="posts")
    author_user: Mapped["User | None"] = relationship("User", foreign_keys=[author_user_id])
    author_persona: Mapped["Persona | None"] = relationship("Persona", foreign_keys=[author_persona_id])
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "(author_user_id IS NOT NULL AND author_persona_id IS NULL) OR "
            "(author_user_id IS NULL AND author_persona_id IS NOT NULL)",
            name="ck_post_exactly_one_author_identity",
        ),
        Index("ix_posts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Post {self.id}:{self.title[:24]!r}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )

    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id"), nullable=True
    )

    post: Mapped[Post] = relationship(back_populates="comments")
    parent: Mapped["Comment | None"] = relationship(remote_side="Comment.id", backref="children")

    __table_args__ = (
        CheckConstraint(
            "(author_user_id IS NOT NULL AND author_persona_id IS NULL) OR "
            "(author_user_id IS NULL AND author_persona_id IS NOT NULL)",
            name="ck_comment_exactly_one_author_identity",
        ),
        Index("ix_comments_post_id_created_at", "post_id", "created_at"),
    )


class SavedPost(db.Model):
    __tablename__ = "saved_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

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
        # PostgreSQL: enforce "one save per identity per post" using partial unique indexes.
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
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

    voted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    voted_by_persona_id: Mapped[int | None] = mapped_column(
        ForeignKey("personas.id"), nullable=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1

    __table_args__ = (
        CheckConstraint("value IN (-1, 1)", name="ck_vote_value"),
        CheckConstraint(
            "(voted_by_user_id IS NOT NULL AND voted_by_persona_id IS NULL) OR "
            "(voted_by_user_id IS NULL AND voted_by_persona_id IS NOT NULL)",
            name="ck_vote_exactly_one_identity",
        ),
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

