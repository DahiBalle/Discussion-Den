/**
 * Feed Modal Logic
 * Handles opening posts in a modal and loading comments.
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeFeedModal();
});

function initializeFeedModal() {
    const feedContainer = document.getElementById('feed-container');
    const modalEl = document.getElementById('postDetailModal');
    if (!modalEl) return;
    
    const modal = new bootstrap.Modal(modalEl);
    let currentPostId = null;

    // Delegate click events for "Comment" buttons and post titles/cards
    feedContainer.addEventListener('click', function(e) {
        // Check if clicked element or parent is a comment button or link to post
        const commentBtn = e.target.closest('a[href*="/post/"], button.btn-action-enhanced:has(.fa-comments)');
        const postLink = e.target.closest('.post-title-enhanced a');
        
        // Prevent default navigation if it's a link to a post
        if (commentBtn || postLink) {
            const target = commentBtn || postLink;
            const href = target.getAttribute('href') || target.dataset.href;
            
            // Extract post ID from URL or data attribute
            // URL format: /post/123
            let postId = null;
            if (href) {
                const match = href.match(/\/post\/(\d+)/);
                if (match) postId = match[1];
            } else {
                // Try finding closest post card
                const card = target.closest('.post-card-enhanced');
                if (card) postId = card.dataset.postId;
            }

            if (postId) {
                e.preventDefault();
                currentPostId = postId;
                openPostModal(modal, postId);
            }
        }
    });

    // Handle comment form submission in modal
    const commentForm = document.getElementById('modal-comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!currentPostId) return;
            
            const formData = new FormData(commentForm);
            const body = formData.get('body');
            
            submitComment(currentPostId, body, null, () => {
                commentForm.reset();
                loadModalComments(currentPostId);
            });
        });
    }
}

function openPostModal(modal, postId) {
    modal.show();
    
    // Show loading state
    document.getElementById('modal-post-content').innerHTML = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    document.getElementById('modal-comments-container').innerHTML = '<div class="text-center text-muted">Loading comments...</div>';
    
    // Fetch Post Details
    fetch(`/api/post/${postId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderModalPost(data.post);
            } else {
                document.getElementById('modal-post-content').innerHTML = '<div class="alert alert-danger">Failed to load post.</div>';
            }
        })
        .catch(err => {
            console.error(err);
            document.getElementById('modal-post-content').innerHTML = '<div class="alert alert-danger">Error loading post.</div>';
        });

    // Fetch Comments
    loadModalComments(postId);
}

function loadModalComments(postId) {
    const container = document.getElementById('modal-comments-container');
    fetch(`/api/post/${postId}/comments`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (data.comments.length === 0) {
                    container.innerHTML = '<div class="text-center text-muted p-3">No comments yet. Be the first!</div>';
                } else {
                    container.innerHTML = renderComments(data.comments, true); // true for "in modal"
                }
            } else {
                container.innerHTML = '<div class="text-danger">Failed to load comments.</div>';
            }
        });
}

function renderModalPost(post) {
    const html = `
        <article class="post-card-enhanced shadow-none border-0 mb-0">
            <header class="post-header-enhanced">
                ${renderAuthorBadge(post)}
                <span class="post-author">${escapeHtml(post.author_name)}</span>
                <span class="text-muted">•</span>
                <span class="post-meta">${formatTimeAgo(post.created_at)}</span>
                 ${post.community_name ? `<span class="text-muted">•</span><span class="text-primary">r/${escapeHtml(post.community_name)}</span>` : ''}
            </header>
            
            <h2 class="post-title-enhanced" style="font-size: 1.5rem;">${escapeHtml(post.title)}</h2>
            
            <div class="post-body-enhanced fs-5">${escapeHtml(post.body || '')}</div>
            
            ${post.image_url ? `<img src="${post.image_url}" class="post-image-enhanced" alt="Post Image">` : ''}
            
            <footer class="action-buttons-enhanced mt-3">
                <div class="action-group">
                    <button class="btn-action-enhanced vote-btn ${post.user_vote === 1 ? 'voted-up' : ''}" 
                            data-post-id="${post.id}" data-vote="1" onclick="handleVoteInline(event, ${post.id}, 1)">
                        <i class="fas fa-arrow-up"></i>
                        <span class="vote-count-up">${post.upvotes}</span>
                    </button>
                    <button class="btn-action-enhanced vote-btn ${post.user_vote === -1 ? 'voted-down' : ''}" 
                            data-post-id="${post.id}" data-vote="-1" onclick="handleVoteInline(event, ${post.id}, -1)">
                        <i class="fas fa-arrow-down"></i>
                        <span class="vote-count-down">${post.downvotes}</span>
                    </button>
                    <button class="btn-action-enhanced save-btn ${post.is_saved ? 'saved' : ''}" 
                            data-post-id="${post.id}" onclick="handleSaveInline(event, ${post.id})">
                        <i class="fas fa-${post.is_saved ? 'bookmark' : 'bookmark-o'}"></i>
                        <span>${post.is_saved ? 'Saved' : 'Save'}</span>
                    </button>
                </div>
            </footer>
        </article>
    `;
    document.getElementById('modal-post-content').innerHTML = html;
}

function renderAuthorBadge(post) {
    if (post.author_persona_id) {
        return `<div class="persona-badge-enhanced persona"><i class="fas fa-mask"></i><span>Persona</span></div>`;
    }
    return `<div class="persona-badge-enhanced user"><i class="fas fa-user"></i><span>User</span></div>`;
}

// Reusing logic from post.js but adapted for generic usage
function renderComments(comments, inModal = false) {
    // Build comment tree
    const commentMap = {};
    const rootComments = [];
    comments.forEach(c => commentMap[c.id] = {...c, replies: []});
    comments.forEach(c => {
        if (c.parent_comment_id && commentMap[c.parent_comment_id]) {
            commentMap[c.parent_comment_id].replies.push(c.id);
        } else {
            rootComments.push(c.id);
        }
    });

    const renderNode = (id, depth) => {
        const c = commentMap[id];
        if (!c) return '';
        const authorName = c.author.name || c.author.username || 'Unknown';
        const badge = c.author.type === 'persona' 
            ? '<span class="badge bg-purple text-white me-2">Persona</span>' 
            : '<span class="badge bg-secondary text-white me-2">User</span>';
            
        return `
            <div class="comment mb-3" style="margin-left: ${depth * 20}px; border-left: 2px solid var(--border-color); padding-left: 15px;">
                <div class="d-flex align-items-center mb-1">
                    ${badge}
                    <strong class="me-2">${escapeHtml(authorName)}</strong>
                    <small class="text-muted">${formatTimeAgo(c.created_at)}</small>
                </div>
                <div class="mb-2">${escapeHtml(c.body)}</div>
                <div class="comment-actions">
                    <button class="btn btn-sm btn-link text-decoration-none p-0" onclick="toggleReplyForm(${c.id})">Reply</button>
                </div>
                <div id="reply-form-${c.id}" class="mt-2" style="display:none;">
                    <textarea id="reply-input-${c.id}" class="form-control mb-2" rows="2" placeholder="Reply..."></textarea>
                    <button class="btn btn-sm btn-primary" onclick="submitReplyInline(${c.id}, ${c.post_id})">Post Reply</button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="toggleReplyForm(${c.id})">Cancel</button>
                </div>
                <!-- Replies -->
                ${c.replies.map(rid => renderNode(rid, depth + 1)).join('')}
            </div>
        `;
    };

    return rootComments.map(id => renderNode(id, 0)).join('');
}

function toggleReplyForm(commentId) {
    const el = document.getElementById(`reply-form-${commentId}`);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function submitReplyInline(parentId, postId) {
    const input = document.getElementById(`reply-input-${parentId}`);
    const body = input.value.trim();
    if (!body) return;

    submitComment(postId, body, parentId, () => {
        loadModalComments(postId); // Refresh comments
    });
}

function submitComment(postId, body, parentId, callback) {
    fetch(`/api/post/${postId}/comment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ body, parent_comment_id: parentId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            callback();
        } else {
            alert(data.error || 'Failed to comment');
        }
    });
}

// Helpers
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimeAgo(dateString) { // Simplified version
    const date = new Date(dateString.includes('Z') ? dateString : dateString + 'Z');
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// Inline Vote/Save handlers (simplified for modal)
function handleVoteInline(e, postId, value) {
    e.stopPropagation();
    // ... Copy valid vote logic or reuse global if available ...
    // For now, just simplistic fetch
    fetch(`/api/post/${postId}/vote`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({vote: value})
    }).then(res => res.json()).then(data => {
        if (data.success) {
            // Update modal UI
            const upSpan = e.target.closest('.action-group').querySelector('.vote-count-up');
            const downSpan = e.target.closest('.action-group').querySelector('.vote-count-down');
            if (upSpan) upSpan.textContent = data.upvotes;
            if (downSpan) downSpan.textContent = data.downvotes;
            
            // Toggle classes
            const btns = e.target.closest('.action-group').querySelectorAll('.vote-btn');
            btns.forEach(b => b.classList.remove('voted-up', 'voted-down'));
            if (data.vote === 1) e.target.closest('.action-group').querySelector('[data-vote="1"]').classList.add('voted-up');
            if (data.vote === -1) e.target.closest('.action-group').querySelector('[data-vote="-1"]').classList.add('voted-down');
        }
    });
}

function handleSaveInline(e, postId) {
    e.stopPropagation();
    const btn = e.target.closest('.save-btn');
    const isSaved = btn.classList.contains('saved');
    fetch(`/api/post/${postId}/save`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({save: !isSaved})
    }).then(res => res.json()).then(data => {
        if (data.success) {
            if (data.is_saved) {
                btn.classList.add('saved');
                btn.querySelector('span').textContent = 'Saved';
                btn.querySelector('i').className = 'fas fa-bookmark';
            } else {
                btn.classList.remove('saved');
                btn.querySelector('span').textContent = 'Save';
                btn.querySelector('i').className = 'fas fa-bookmark-o';
            }
        }
    });
}
