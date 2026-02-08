/**
 * Post Detail Page JavaScript
 * Handles voting, saving, and nested comment toggling
 */

document.addEventListener('DOMContentLoaded', function() {
    // Setup vote buttons
    setupVoteButtons();
    
    // Setup save button
    setupSaveButton();
    
    // Setup comment toggles
    setupCommentToggles();
    
    // Setup comment form submission
    setupCommentForm();
});

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
    const upBtn = document.querySelector(`.vote-btn[data-post-id="${postId}"][data-vote="1"]`);
    const downBtn = document.querySelector(`.vote-btn[data-post-id="${postId}"][data-vote="-1"]`);
    
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
 * Setup save button handler
 */
function setupSaveButton() {
    const saveButton = document.querySelector('.save-btn');
    if (saveButton) {
        saveButton.addEventListener('click', handleSave);
    }
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
    const saveBtn = document.querySelector(`.save-btn[data-post-id="${postId}"]`);
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
 * Setup comment toggle handlers for nested comments
 */
function setupCommentToggles() {
    const toggleButtons = document.querySelectorAll('.comment-toggle');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.getAttribute('data-comment-id');
            toggleCommentReplies(commentId);
        });
    });
}

/**
 * Toggle visibility of nested comment replies
 */
function toggleCommentReplies(commentId) {
    const repliesContainer = document.getElementById(`replies-${commentId}`);
    const toggleBtn = document.querySelector(`.comment-toggle[data-comment-id="${commentId}"]`);
    
    if (!repliesContainer || !toggleBtn) return;
    
    const isHidden = repliesContainer.style.display === 'none';
    repliesContainer.style.display = isHidden ? 'block' : 'none';
    toggleBtn.textContent = isHidden ? 'Hide replies' : 'Show replies';
}

/**
 * Setup comment form submission
 */
function setupCommentForm() {
    const commentForm = document.getElementById('comment-form');
    if (!commentForm) return;
    
    commentForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(commentForm);
        const postId = formData.get('post_id');
        const body = formData.get('body');
        const parentId = formData.get('parent_comment_id') || null;
        
        fetch(`/api/post/${postId}/comment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                body: body,
                parent_comment_id: parentId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload page to show new comment
                window.location.reload();
            } else {
                alert('Failed to post comment: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error posting comment:', error);
            alert('Error posting comment. Please try again.');
        });
    });
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
