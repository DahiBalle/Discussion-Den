/**
 * Feed Page JavaScript
 * Handles infinite scroll, voting, and saving posts
 */

let currentPage = 1;
let isLoading = false;
let hasMore = true;

document.addEventListener('DOMContentLoaded', function() {
    const feedContainer = document.getElementById('feed-container');
    if (!feedContainer) return;
    
    // Initialize infinite scroll
    setupInfiniteScroll();
    
    // Setup vote buttons
    setupVoteButtons();
    
    // Setup save buttons
    setupSaveButtons();
});

/**
 * Setup infinite scroll for feed
 */
function setupInfiniteScroll() {
    const feedContainer = document.getElementById('feed-container');
    if (!feedContainer) return;
    
    // Check if there are already posts rendered server-side
    const existingPosts = feedContainer.querySelectorAll('.post-card');
    if (existingPosts.length === 0) {
        // Load first page if no posts exist
        loadMorePosts();
    } else {
        // Start from page 2 if posts already exist
        currentPage = 2;
    }
    
    window.addEventListener('scroll', function() {
        if (isLoading || !hasMore) return;
        
        // Check if user is near bottom of page
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000) {
            loadMorePosts();
        }
    });
}

/**
 * Load more posts via AJAX
 */
function loadMorePosts() {
    if (isLoading || !hasMore) return;
    
    isLoading = true;
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    
    fetch(`/api/feed?page=${currentPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.posts) {
                const feedContainer = document.getElementById('feed-container');
                if (feedContainer && data.posts.length > 0) {
                    data.posts.forEach(post => {
                        const postElement = createPostElement(post);
                        feedContainer.appendChild(postElement);
                    });
                    
                    currentPage++;
                    hasMore = data.has_more || false;
                } else {
                    hasMore = false;
                }
            } else {
                hasMore = false;
            }
        })
        .catch(error => {
            console.error('Error loading posts:', error);
            hasMore = false;
        })
        .finally(() => {
            isLoading = false;
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        });
}

/**
 * Create a post DOM element from JSON data
 */
function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'post-card';
    div.setAttribute('data-post-id', post.id);
    
    const authorBadge = post.author_persona_id 
        ? '<span class="persona-badge">Persona</span>' 
        : '<span class="user-badge">User</span>';
    
    const timeAgo = formatTimeAgo(post.created_at);
    
    div.innerHTML = `
        <div class="post-header">
            ${authorBadge}
            <span class="post-author">${escapeHtml(post.author_name)}</span>
            <span class="text-muted-custom">•</span>
            <span class="post-meta">${timeAgo}</span>
            ${post.community_name ? `<span class="text-muted-custom">•</span><span class="post-meta">r/${escapeHtml(post.community_name)}</span>` : ''}
        </div>
        <h3 class="post-title">
            <a href="/post/${post.id}" style="color: inherit; text-decoration: none;">${escapeHtml(post.title)}</a>
        </h3>
        ${post.body ? `<div class="post-body">${escapeHtml(post.body)}</div>` : ''}
        ${post.image_url ? `<img src="${escapeHtml(post.image_url)}" alt="Post image" class="post-image">` : ''}
        <div class="action-buttons">
            <button class="btn-action vote-btn ${post.user_vote === 1 ? 'voted-up' : ''}" 
                    data-post-id="${post.id}" data-vote="1">
                ▲ ${post.upvotes || 0}
            </button>
            <button class="btn-action vote-btn ${post.user_vote === -1 ? 'voted-down' : ''}" 
                    data-post-id="${post.id}" data-vote="-1">
                ▼ ${post.downvotes || 0}
            </button>
            <button class="btn-action save-btn ${post.is_saved ? 'saved' : ''}" 
                    data-post-id="${post.id}">
                ${post.is_saved ? '★ Saved' : '☆ Save'}
            </button>
            <a href="/post/${post.id}" class="btn-action">💬 ${post.comment_count || 0} Comments</a>
        </div>
    `;
    
    // Re-attach event listeners
    const voteBtns = div.querySelectorAll('.vote-btn');
    voteBtns.forEach(btn => {
        btn.addEventListener('click', handleVote);
    });
    
    const saveBtn = div.querySelector('.save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', handleSave);
    }
    
    return div;
}

/**
 * Setup vote button handlers
 */
function setupVoteButtons() {
    const voteButtons = document.querySelectorAll('.vote-btn');
    voteButtons.forEach(btn => {
        btn.addEventListener('click', handleVote);
    });
}

/**
 * Handle vote action via AJAX
 */
function handleVote(e) {
    e.preventDefault();
    const postId = this.getAttribute('data-post-id');
    const voteValue = parseInt(this.getAttribute('data-vote'));
    
    fetch(`/api/post/${postId}/vote`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ vote: voteValue })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateVoteUI(postId, data.vote, data.upvotes, data.downvotes);
        } else {
            alert('Failed to vote: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error voting:', error);
        alert('Error voting. Please try again.');
    });
}

/**
 * Update vote UI after successful vote
 */
function updateVoteUI(postId, userVote, upvotes, downvotes) {
    const postCard = document.querySelector(`[data-post-id="${postId}"]`);
    if (!postCard) return;
    
    const upBtn = postCard.querySelector(`.vote-btn[data-vote="1"]`);
    const downBtn = postCard.querySelector(`.vote-btn[data-vote="-1"]`);
    
    // Reset classes
    if (upBtn) {
        upBtn.classList.remove('voted-up', 'voted-down');
        upBtn.innerHTML = `▲ ${upvotes || 0}`;
    }
    if (downBtn) {
        downBtn.classList.remove('voted-up', 'voted-down');
        downBtn.innerHTML = `▼ ${downvotes || 0}`;
    }
    
    // Apply new vote state
    if (userVote === 1 && upBtn) {
        upBtn.classList.add('voted-up');
    } else if (userVote === -1 && downBtn) {
        downBtn.classList.add('voted-down');
    }
}

/**
 * Setup save button handlers
 */
function setupSaveButtons() {
    const saveButtons = document.querySelectorAll('.save-btn');
    saveButtons.forEach(btn => {
        btn.addEventListener('click', handleSave);
    });
}

/**
 * Handle save/unsave action via AJAX
 */
function handleSave(e) {
    e.preventDefault();
    const postId = this.getAttribute('data-post-id');
    const isCurrentlySaved = this.classList.contains('saved');
    
    fetch(`/api/post/${postId}/save`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ save: !isCurrentlySaved })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateSaveUI(postId, data.is_saved);
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving:', error);
        alert('Error saving. Please try again.');
    });
}

/**
 * Update save UI after successful save/unsave
 */
function updateSaveUI(postId, isSaved) {
    const postCard = document.querySelector(`[data-post-id="${postId}"]`);
    if (!postCard) return;
    
    const saveBtn = postCard.querySelector('.save-btn');
    if (!saveBtn) return;
    
    if (isSaved) {
        saveBtn.classList.add('saved');
        saveBtn.innerHTML = '★ Saved';
    } else {
        saveBtn.classList.remove('saved');
        saveBtn.innerHTML = '☆ Save';
    }
}

/**
 * Get CSRF token
 */
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    return '';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format time ago string
 */
function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}
