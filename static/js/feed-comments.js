/**
 * Feed Inline Comments Logic
 * Handles expanding posts to show comments inline.
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeInlineComments();
});

function initializeInlineComments() {
    const feedContainer = document.getElementById('feed-container');

    // Delegate click events
    feedContainer.addEventListener('click', function (e) {
        // 1. Toggle Comments
        const commentBtn = e.target.closest('a.btn-action-enhanced[href*="/post/"], button.btn-action-enhanced:has(.fa-comments)');

        // If it's a link (navigation), allow default behavior
        if (commentBtn && commentBtn.tagName === 'A') {
            return;
        }

        if (commentBtn) {
            e.preventDefault();
            // Try getting ID from data attribute or finding closest card
            let postId = commentBtn.dataset.postId;
            if (!postId) {
                const card = commentBtn.closest('.post-card-enhanced');
                if (card) postId = card.dataset.postId;
            }

            if (postId) {
                toggleCommentsSection(postId);
            }
        }
    });

    // Handle Comment Forms (delegated)
    feedContainer.addEventListener('submit', function (e) {
        if (e.target.matches('.inline-comment-form')) {
            e.preventDefault();
            const form = e.target;
            const postId = form.dataset.postId;
            const input = form.querySelector('textarea[name="body"]');
            const body = input.value.trim();

            if (!body) return;

            submitComment(postId, body, null, () => {
                input.value = '';
                input.style.height = ''; // Reset auto-resize
                reloadComments(postId);
            });
        }
    });
}

function toggleCommentsSection(postId) {
    const section = document.getElementById(`comments-section-${postId}`);
    if (!section) return;

    const isHidden = section.style.display === 'none';
    section.style.display = isHidden ? 'block' : 'none';

    // If opening and empty, fetch comments
    if (isHidden && !section.dataset.loaded) {
        loadComments(postId);
    }
}

function loadComments(postId) {
    const section = document.getElementById(`comments-section-${postId}`);
    const container = section.querySelector('.comments-container');
    const spinner = section.querySelector('.loading-spinner');

    spinner.style.display = 'block';
    container.innerHTML = ''; // Clear prev if any

    fetch(`/api/post/${postId}/comments`)
        .then(res => res.json())
        .then(data => {
            section.dataset.loaded = 'true';
            spinner.style.display = 'none';

            if (data.success) {
                if (data.comments.length === 0) {
                    container.innerHTML = '<div class="text-muted text-center py-3">No comments yet.</div>';
                } else {
                    container.innerHTML = renderComments(data.comments);
                    // Re-initialize any logic if needed (e.g. tooltips)
                }
            } else {
                container.innerHTML = '<div class="text-danger">Failed to load comments.</div>';
            }
        })
        .catch(err => {
            console.error(err);
            spinner.style.display = 'none';
            container.innerHTML = '<div class="text-danger">Error loading comments.</div>';
        });
}

function reloadComments(postId) {
    const section = document.getElementById(`comments-section-${postId}`);
    section.dataset.loaded = ''; // Force reload
    loadComments(postId);
}

function renderComments(comments) {
    // Build Map (Adjacency List -> Tree structure)
    // 1. Initialize map with all comments
    // 2. Identify root comments (no parent_id)
    // 3. Populate replies arrays for each comment
    const commentMap = {};
    const rootComments = [];
    comments.forEach(c => commentMap[c.id] = { ...c, replies: [] });
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

        // Threading visual: Add left border for depth > 0
        const nestingStyle = depth > 0
            ? `margin-left: 24px; padding-left: 12px; border-left: 2px solid var(--border-color);`
            : `border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 12px;`;

        const badge = c.author.type === 'persona'
            ? '<span class="badge bg-purple text-white ms-2" style="font-size: 0.7em;">Persona</span>'
            : '';

        // Limit visible replies to keep UI clean
        // Shows only 1 reply by default, hides the rest behind a "View more" button
        const replyLimit = 1;
        const totalReplies = c.replies.length;
        let visibleReplies = c.replies;
        let hiddenReplies = [];

        if (totalReplies > replyLimit) {
            visibleReplies = c.replies.slice(0, replyLimit);
            hiddenReplies = c.replies.slice(replyLimit);
        }

        return `
            <div class="comment-item" style="${nestingStyle}">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <div class="d-flex align-items-center">
                        <strong class="small text-primary">${escapeHtml(authorName)}</strong>
                        ${badge}
                        <span class="text-muted mx-2">•</span>
                        <small class="text-muted" style="font-size: 0.85em;">${formatTimeAgo(c.created_at)}</small>
                    </div>
                </div>
                
                <div class="comment-body mb-2 text-wrap text-secondary" style="word-break: break-word; font-size: 0.95rem;">${escapeHtml(c.body)}</div>
                
                <div class="comment-actions d-flex gap-3 align-items-center mb-2">
                    <button class="btn btn-link btn-sm p-0 text-decoration-none text-primary fw-bold d-flex align-items-center" onclick="toggleInlineReplyForm(${c.id})">
                        <i class="fas fa-reply me-1"></i>Reply
                    </button>
                </div>

                <!-- Reply Form (Hidden) -->
                <div id="reply-form-${c.id}" class="inline-reply-container mt-2 mb-3 ps-2 border-start border-primary border-2" style="display:none;">
                    <div class="d-flex gap-2 align-items-end">
                        <textarea id="reply-input-${c.id}" class="form-control form-control-sm" rows="1" 
                            placeholder="Reply to ${escapeHtml(authorName)}..." 
                            style="resize:none; overflow:hidden; min-height: 32px;" 
                            oninput="this.style.height = ''; this.style.height = this.scrollHeight + 'px'"></textarea>
                        <button class="btn btn-sm btn-primary" onclick="submitReplyInline(${c.id}, ${c.post_id})">Reply</button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="toggleInlineReplyForm(${c.id})">Cancel</button>
                    </div>
                </div>

                <!-- Recursion for replies -->
                <div class="replies-container">
                    ${visibleReplies.map(rid => renderNode(rid, depth + 1)).join('')}
                    
                    ${hiddenReplies.length > 0 ? `
                        <button class="btn btn-sm btn-light text-primary rounded-pill mt-2 mb-2" 
                                onclick="this.nextElementSibling.style.display='block'; this.remove()">
                            <i class="fas fa-plus me-1"></i> View ${hiddenReplies.length} more replies
                        </button>
                        <div style="display:none;">
                            ${hiddenReplies.map(rid => renderNode(rid, depth + 1)).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    };

    // Logic for limiting root comments
    const rootLimit = 1;
    let visibleRoot = rootComments;
    let hiddenRoot = [];

    if (rootComments.length > rootLimit) {
        visibleRoot = rootComments.slice(0, rootLimit);
        hiddenRoot = rootComments.slice(rootLimit);
    }

    let html = visibleRoot.map(id => renderNode(id, 0)).join('');

    if (hiddenRoot.length > 0) {
        html += `
            <button class="btn btn-sm btn-light text-primary rounded-pill mt-3 w-100" 
                    onclick="this.nextElementSibling.style.display='block'; this.remove()">
                <i class="fas fa-comments me-1"></i> View ${hiddenRoot.length} more comments
            </button>
            <div style="display:none;">
                ${hiddenRoot.map(id => renderNode(id, 0)).join('')}
            </div>
        `;
    }

    return html;
}

// Global functions for inline usage
window.toggleInlineReplyForm = function (commentId) {
    const isAuth = document.querySelector('meta[name="user-authenticated"]')?.content === 'true';

    if (!isAuth) {
        // user is not logged in -> show auth modal
        const authModalEl = document.getElementById('authModal');
        if (authModalEl) {
            const modal = bootstrap.Modal.getOrCreateInstance(authModalEl);
            modal.show();
        }
        return;
    }

    const currentEl = document.getElementById(`reply-form-${commentId}`);
    if (!currentEl) return;

    const isOpening = currentEl.style.display === 'none';

    if (isOpening) {
        // Close ALL other reply forms first
        document.querySelectorAll('.inline-reply-container').forEach(el => {
            if (el.id !== `reply-form-${commentId}`) {
                el.style.display = 'none';
            }
        });

        // Open this one
        currentEl.style.display = 'block';
        const input = document.getElementById(`reply-input-${commentId}`);
        if (input) input.focus();
    } else {
        // Simply close
        currentEl.style.display = 'none';
    }
}

window.submitReplyInline = function (parentId, postId) {
    const input = document.getElementById(`reply-input-${parentId}`);
    const body = input.value.trim();
    if (!body) return;



    submitComment(postId, body, parentId, () => {
        reloadComments(postId);
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
        })
        .catch(err => console.error(err));
}

// Utils
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimeAgo(dateString) {
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
