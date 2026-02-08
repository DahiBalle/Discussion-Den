/**
 * Discussion Den - Theme and UI Enhancement JavaScript
 * Handles smooth interactions, animations, and UI feedback
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeAnimations();
    initializeInteractions();
    initializeNavbar();
});

/**
 * Initialize theme system
 */
function initializeTheme() {
    // Add smooth transitions to all elements
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Add loading animation to page
    document.body.classList.add('animate-fade-in-up');
    
    // Initialize scroll effects
    initializeScrollEffects();
}

/**
 * Update navbar background to match current theme and scroll position.
 * Call this when theme changes so navbar doesn't keep the previous theme's inline style.
 */
function updateNavbarBackground() {
    const navbar = document.getElementById('main-navbar');
    if (!navbar) return;
    const theme = document.documentElement.getAttribute('data-theme') || localStorage.getItem('theme') || 'dark';
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    navbar.style.backdropFilter = 'blur(20px)';
    if (theme === 'light') {
        navbar.style.background = 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 249, 250, 0.98) 100%)';
    } else {
        navbar.style.background = scrollTop > 50 ? 'rgba(15, 20, 25, 0.98)' : 'rgba(15, 20, 25, 0.95)';
    }
}

/**
 * Initialize scroll effects
 */
function initializeScrollEffects() {
    const navbar = document.getElementById('main-navbar');
    if (!navbar) return;

    updateNavbarBackground();

    window.addEventListener('scroll', function() {
        updateNavbarBackground();
    });
}

/**
 * Initialize animations for elements
 */
function initializeAnimations() {
    // Animate cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all cards
    document.querySelectorAll('.card').forEach(card => {
        observer.observe(card);
    });
    
    // Add stagger animation to multiple cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

/**
 * Initialize interactive elements
 */
function initializeInteractions() {
    // Enhanced button interactions
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
        
        button.addEventListener('mousedown', function() {
            this.style.transform = 'translateY(0) scale(0.98)';
        });
        
        button.addEventListener('mouseup', function() {
            this.style.transform = 'translateY(-2px) scale(1)';
        });
    });
    
    // Enhanced card interactions
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.3)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
        });
    });
    
    // Enhanced form interactions
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    });
    
    // Add ripple effect to buttons
    addRippleEffect();
}

/**
 * Add ripple effect to buttons
 */
function addRippleEffect() {
    document.querySelectorAll('.btn-primary, .btn-secondary').forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Add ripple CSS
    const style = document.createElement('style');
    style.textContent = `
        .btn {
            position: relative;
            overflow: hidden;
        }
        
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(0);
            animation: ripple-animation 0.6s linear;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Hide search suggestions dropdown
 */
function hideSearchSuggestions() {
    const el = document.getElementById('search-suggestions-dropdown');
    if (el) {
        el.classList.remove('open');
        el.innerHTML = '';
    }
}

/**
 * Render search suggestions dropdown (posts, communities, users) or "Not found"
 */
function renderSearchSuggestions(data, query) {
    const dropdown = document.getElementById('search-suggestions-dropdown');
    if (!dropdown) return;
    const posts = data.posts || [];
    const communities = data.communities || [];
    const users = data.users || [];
    const hasAny = posts.length > 0 || communities.length > 0 || users.length > 0;

    if (!hasAny) {
        dropdown.innerHTML = '<div class="search-suggest-item search-suggest-notfound">Not found</div>';
    } else {
        var html = '';
        if (posts.length > 0) {
            html += '<div class="search-suggest-section">Posts</div>';
            posts.forEach(function(p) {
                html += '<a class="search-suggest-item" href="' + (p.url || '#') + '"><i class="fas fa-file-alt me-2"></i>' + escapeHtml((p.title || '').slice(0, 60)) + (p.title && p.title.length > 60 ? '...' : '') + '</a>';
            });
        }
        if (communities.length > 0) {
            html += '<div class="search-suggest-section">Communities</div>';
            communities.forEach(function(c) {
                html += '<a class="search-suggest-item" href="' + (c.url || '#') + '"><i class="fas fa-users me-2"></i>r/' + escapeHtml(c.name || '') + '</a>';
            });
        }
        if (users.length > 0) {
            html += '<div class="search-suggest-section">Users</div>';
            users.forEach(function(u) {
                html += '<a class="search-suggest-item" href="' + (u.url || '#') + '"><i class="fas fa-user me-2"></i>' + escapeHtml(u.username || '') + '</a>';
            });
        }
        dropdown.innerHTML = html;
    }
    dropdown.classList.add('open');
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize navbar enhancements
 */
function initializeNavbar() {
    const searchInput = document.getElementById('navbar-search-input');
    const searchContainer = document.querySelector('.search-container');
    const searchWrapper = document.querySelector('.navbar-search-wrapper');
    const suggestionsDropdown = document.getElementById('search-suggestions-dropdown');

    // Offcanvas "Search" link: close offcanvas and focus navbar search (no navigation to /search)
    document.querySelectorAll('.offcanvas-focus-navbar-search').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const offcanvasEl = document.getElementById('sidebarOffcanvas');
            if (offcanvasEl && typeof bootstrap !== 'undefined') {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (bsOffcanvas) bsOffcanvas.hide();
            }
            if (searchInput) searchInput.focus();
        });
    });

    if (searchInput && searchContainer) {
        searchInput.addEventListener('focus', function() {
            searchContainer.style.transform = 'scale(1.05)';
            searchContainer.style.boxShadow = '0 0 0 3px rgba(0, 212, 255, 0.2)';
        });

        searchInput.addEventListener('blur', function() {
            searchContainer.style.transform = 'scale(1)';
            searchContainer.style.boxShadow = 'none';
            setTimeout(function() { hideSearchSuggestions(); }, 200);
        });
    }

    // Search suggestions: debounced fetch, dropdown, "Not found" when empty
    if (searchInput && suggestionsDropdown && searchWrapper) {
        const suggestUrl = searchWrapper.getAttribute('data-suggest-url') || '/search/suggest';
        let suggestDebounce = null;

        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            clearTimeout(suggestDebounce);
            if (query.length < 2) {
                hideSearchSuggestions();
                return;
            }
            suggestDebounce = setTimeout(function() {
                fetch(suggestUrl + '?q=' + encodeURIComponent(query))
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        renderSearchSuggestions(data, query);
                    })
                    .catch(function() {
                        suggestionsDropdown.innerHTML = '<div class="search-suggest-item search-suggest-notfound">Not found</div>';
                        suggestionsDropdown.classList.add('open');
                    });
            }, 300);
        });

        searchWrapper.querySelector('form')?.addEventListener('submit', function() {
            hideSearchSuggestions();
        });
    }

    // Enhanced dropdown animations
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const menu = this.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu-enhanced')) {
                setTimeout(() => {
                    menu.style.animation = 'slideInRight 0.3s ease-out';
                }, 10);
            }
        });
    });
}

/**
 * Utility function to show toast notifications
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-enhanced`;
    toast.innerHTML = `
        <div class="alert-content">
            <div class="alert-icon">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'}"></i>
            </div>
            <div class="alert-message">${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-enhanced" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add to flash container or create one
    let flashContainer = document.querySelector('.flash-container');
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.className = 'flash-container';
        document.body.appendChild(flashContainer);
    }
    
    flashContainer.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

/**
 * Enhanced loading states
 */
function showLoading(element, text = 'Loading...') {
    const originalContent = element.innerHTML;
    element.innerHTML = `
        <span class="loading-spinner"></span>
        <span class="ms-2">${text}</span>
    `;
    element.disabled = true;
    
    // Add loading spinner CSS if not exists
    if (!document.querySelector('#loading-spinner-css')) {
        const style = document.createElement('style');
        style.id = 'loading-spinner-css';
        style.textContent = `
            .loading-spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: currentColor;
                animation: spin 1s ease-in-out infinite;
            }
        `;
        document.head.appendChild(style);
    }
    
    return originalContent;
}

function hideLoading(element, originalContent) {
    element.innerHTML = originalContent;
    element.disabled = false;
}

/**
 * Smooth page transitions
 */
function smoothTransition(url) {
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        window.location.href = url;
    }, 300);
}

// Export functions for global use
window.DiscussionDenTheme = {
    showToast,
    showLoading,
    hideLoading,
    smoothTransition,
    updateNavbarBackground
};