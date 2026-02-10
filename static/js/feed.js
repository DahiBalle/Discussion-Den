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
/**
 * Setup infinite scroll for feed.
 * 
 * Logic:
 * 1. Checks if server-side rendered posts exist (Page 1).
 * 2. If so, initializes `currentPage` to 2.
 * 3. Uses a scroll event listener to detect when user is near bottom.
 * 4. Threshold is set to 1000px to pre-load content before user hits bottom.
 */
function setupInfiniteScroll() {
    const feedContainer = document.getElementById('feed-container');
    if (!feedContainer) return;
    
    // Check if there are already posts rendered server-side
    // This allows us to combine SEO-friendly SSR with dynamic infinite scroll
    const existingPosts = feedContainer.querySelectorAll('.post-card');
    if (existingPosts.length === 0) {
        // Load first page if no posts exist (e.g., if template rendered empty container)
        loadMorePosts();
    } else {
        // Start from page 2 if posts already exist to avoid duplicating Page 1
        currentPage = 2;
    }
    
    window.addEventListener('scroll', function() {
        if (isLoading || !hasMore) return;
        
        // Check if user is near bottom of page (within 1000px)
        // Large threshold ensures seamless experience on fast connections
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000) {
            loadMorePosts();
        }
    });
}

/**
 * Load more posts via AJAX
 */
/**
 * Load more posts via AJAX.
 * 
 * Interaction Flow:
 * 1. Sets loading state to prevent duplicate requests.
 * 2. Fetches next page of posts from `/api/feed`.
 * 3. Appends new posts to the container.
 * 4. Updates `currentPage` and `hasMore` flags.
 * 5. Handles empty states and errors with user-friendly UI.
 */
function loadMorePosts() {
    if (isLoading || !hasMore) return;
    
    isLoading = true;
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    
    console.log(`Loading posts page ${currentPage}...`); // Debug log
    
    fetch(`/api/feed?page=${currentPage}`)
        .then(response => {
            console.log('Feed API response status:', response.status); // Debug log
            return response.json();
        })
        .then(data => {
            console.log('Feed API data:', data); // Debug log
            
            if (data.success && data.posts) {
                const feedContainer = document.getElementById('feed-container');
                if (feedContainer && data.posts.length > 0) {
                    console.log(`Adding ${data.posts.length} posts to feed`); // Debug log
                    
                    data.posts.forEach((post, index) => {
                        try {
                            const postElement = createPostElement(post);
                            feedContainer.appendChild(postElement);
                        } catch (error) {
                            console.error(`Error creating post element ${index}:`, error, post);
                        }
                    });
                    
                    currentPage++;
                    hasMore = data.has_more || false;
                    
                    console.log(`Page ${currentPage - 1} loaded. Has more: ${hasMore}`); // Debug log
                } else {
                    console.log('No posts in response or no feed container'); // Debug log
                    hasMore = false;
                }
            } else {
                console.log('API response not successful or no posts:', data); // Debug log
                hasMore = false;
                
                // Show error message if this is the first page and no posts loaded
                if (currentPage === 1) {
                    const feedContainer = document.getElementById('feed-container');
                    if (feedContainer && feedContainer.children.length === 0) {
                        feedContainer.innerHTML = `
                            <div class="card">
                                <div class="card-body text-center py-5">
                                    <div class="mb-4">
                                        <div style="font-size: 4rem; color: var(--text-muted); margin-bottom: 1rem;">⚠️</div>
                                        <h3 class="h4 mb-3">Unable to load posts</h3>
                                        <p class="text-muted-custom mb-4">There was an error loading posts. Please refresh the page to try again.</p>
                                    </div>
                                    <button onclick="window.location.reload()" class="btn btn-primary">Refresh Page</button>
                                </div>
                            </div>
                        `;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading posts:', error);
            hasMore = false;
            
            // Show error message if this is the first page
            if (currentPage === 1) {
                const feedContainer = document.getElementById('feed-container');
                if (feedContainer && feedContainer.children.length === 0) {
                    feedContainer.innerHTML = `
                        <div class="card">
                            <div class="card-body text-center py-5">
                                <div class="mb-4">
                                    <div style="font-size: 4rem; color: var(--text-muted); margin-bottom: 1rem;">🔌</div>
                                    <h3 class="h4 mb-3">Connection Error</h3>
                                    <p class="text-muted-custom mb-4">Unable to connect to the server. Please check your internet connection and try again.</p>
                                </div>
                                <button onclick="window.location.reload()" class="btn btn-primary">Try Again</button>
                            </div>
                        </div>
                    `;
                }
            }
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
    try {
        const div = document.createElement('div');
        div.className = 'post-card';
        div.setAttribute('data-post-id', post.id);

        const authorBadge = post.author_persona_id
            ? '<span class="persona-badge">Persona</span>'
            : '<span class="user-badge">User</span>';

        // Safe time formatting with fallback
        let timeAgo = 'unknown';
        try {
            timeAgo = formatTimeAgo(post.created_at);
        } catch (timeError) {
            console.warn('Error formatting time for post', post.id, timeError);
            timeAgo = 'recently';
        }

        div.innerHTML = `
            <div class="post-header">
                ${authorBadge}
                <span class="post-author">${escapeHtml(post.author_name || 'Unknown')}</span>
                <span class="text-muted-custom">•</span>
                <span class="post-meta">${timeAgo}</span>
                ${post.community_name ? `<span class="text-muted-custom">•</span><span class="post-meta"><a href="/community/${escapeHtml(post.community_name)}" style="color: var(--accent-primary); text-decoration: none;">r/${escapeHtml(post.community_name)}</a></span>` : ''}
            </div>
            <h3 class="post-title">
                <a href="/post/${post.id}" style="color: inherit; text-decoration: none;">${escapeHtml(post.title || 'Untitled')}</a>
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

    } catch (error) {
        console.error('Error creating post element:', error, 'Post data:', post);

        // Return a minimal error post element to prevent complete failure
        const errorDiv = document.createElement('div');
        errorDiv.className = 'post-card';
        errorDiv.innerHTML = `
            <div class="post-header">
                <span class="user-badge">Error</span>
                <span class="post-author">System</span>
                <span class="text-muted-custom">•</span>
                <span class="post-meta">recently</span>
            </div>
            <h3 class="post-title">Error loading post</h3>
            <div class="post-body">There was an error loading this post. Please refresh the page.</div>
        `;
        return errorDiv;
    }
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
    const postVoteBtns = document.querySelectorAll('.vote-btn[data-post-id="' + postId + '"]');
    postVoteBtns.forEach(function(btn) { btn.disabled = true; });

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
    })
    .finally(function() {
        postVoteBtns.forEach(function(btn) { btn.disabled = false; });
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
 * Format time ago string - matches server-side timeago filter logic exactly
 */
function formatTimeAgo(dateString) {
    // Fallback implementation (matches utils.js)
    if (!dateString) {
        return 'unknown';
    }
    
    try {
        const date = new Date(dateString + (dateString.includes('Z') ? '' : 'Z'));
        const now = new Date();
        
        if (isNaN(date.getTime())) {
            return 'unknown';
        }
        
        const diffMs = now.getTime() - date.getTime();
        
        if (diffMs < 0) {
            return 'just now';
        }
        
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffSeconds / 3600);
        const diffDays = Math.floor(diffSeconds / 86400);
        
        if (diffDays > 365) {
            const years = Math.floor(diffDays / 365);
            return `${years}y ago`;
        } else if (diffDays > 30) {
            const months = Math.floor(diffDays / 30);
            return `${months}mo ago`;
        } else if (diffDays > 7) {
            const weeks = Math.floor(diffDays / 7);
            return `${weeks}w ago`;
        } else if (diffDays > 0) {
            return `${diffDays}d ago`;
        } else if (diffHours > 0) {
            return `${diffHours}h ago`;
        } else if (diffMins > 0) {
            return `${diffMins}m ago`;
        }
        
        return 'just now';
        
    } catch (error) {
        console.warn('Error formatting time ago:', error);
        return 'unknown';
    }
}
