from __future__ import annotations

from flask import Blueprint, render_template, request
from sqlalchemy import or_

from extensions import db
from models import Post, Community, User

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.get("/")
def search():
    """
    Global search functionality for posts, communities, and users.
    
    Features:
    - Full-text search across posts (title and body)
    - Community name and description search
    - User username search
    - Pagination with 20 results per page
    - Safe handling of empty queries
    
    Query Parameters:
        q (str): Search query
        type (str): Search type ('all', 'posts', 'communities', 'users')
        page (int): Page number for pagination
    
    Returns:
        Rendered search results template with results and pagination
    """
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    
    results = {
        'posts': [],
        'communities': [],
        'users': [],
        'query': query,
        'type': search_type
    }
    
    if not query or len(query) < 2:
        return render_template('search/results.html', **results)
    
    try:
        # Search posts
        if search_type in ['all', 'posts']:
            posts_query = Post.query.filter(
                or_(
                    Post.title.ilike(f'%{query}%'),
                    Post.body.ilike(f'%{query}%')
                )
            ).order_by(Post.created_at.desc())
            
            if search_type == 'posts':
                posts = posts_query.paginate(
                    page=page, per_page=20, error_out=False
                )
                results['posts'] = posts.items
                results['pagination'] = posts
            else:
                results['posts'] = posts_query.limit(5).all()
        
        # Search communities
        if search_type in ['all', 'communities']:
            communities_query = Community.query.filter(
                or_(
                    Community.name.ilike(f'%{query}%'),
                    Community.description.ilike(f'%{query}%')
                )
            ).order_by(Community.created_at.desc())
            
            if search_type == 'communities':
                communities = communities_query.paginate(
                    page=page, per_page=20, error_out=False
                )
                results['communities'] = communities.items
                results['pagination'] = communities
            else:
                results['communities'] = communities_query.limit(5).all()
        
        # Search users
        if search_type in ['all', 'users']:
            users_query = User.query.filter(
                User.username.ilike(f'%{query}%')
            ).order_by(User.username)
            
            if search_type == 'users':
                users = users_query.paginate(
                    page=page, per_page=20, error_out=False
                )
                results['users'] = users.items
                results['pagination'] = users
            else:
                results['users'] = users_query.limit(5).all()
                
    except Exception as e:
        print(f"Search error: {e}")
        # Return empty results on error
        pass
    
    return render_template('search/results.html', **results)