from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from forms import PostForm
from models import Community


feed_bp = Blueprint("feed", __name__)


@feed_bp.get("/feed")
@login_required
def feed():
    """
    Feed is rendered as a shell; posts are filled by JS via /api/feed (infinite scroll).
    This keeps the page fast and enables persona-aware interactions without reloads.
    """
    from routes.utils import get_identity
    community = Community.query.filter_by(name="campus").first()
    form = PostForm()
    ident = get_identity()
    # Pass empty posts list - JS will load them
    return render_template("feed.html", community=community, post_form=form, posts=[], active_identity=ident)

