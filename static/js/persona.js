/**
 * Persona Switcher
 * Handles switching between user identity and personas via AJAX
 */

document.addEventListener('DOMContentLoaded', function() {
    const personaSwitchOptions = document.querySelectorAll('.persona-switch-option');
    const activeIdentityDisplay = document.getElementById('active-identity-display');
    
    personaSwitchOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const personaId = this.getAttribute('data-persona-id');
            switchPersona(personaId);
        });
    });
    
    /**
     * Switch active persona via AJAX POST request
     * Updates session and reloads feed
     */
    function switchPersona(personaId) {
        const formData = new FormData();
        formData.append('persona_id', personaId === 'null' ? '' : personaId);
        
        fetch('/api/persona/switch', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update display
                if (activeIdentityDisplay) {
                    if (data.persona_id) {
                        activeIdentityDisplay.innerHTML = '<span class="persona-badge">Persona</span>';
                    } else {
                        activeIdentityDisplay.innerHTML = '<span class="user-badge">User</span>';
                    }
                }
                
                // Reload page to reflect new identity context
                window.location.reload();
            } else {
                alert('Failed to switch persona: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error switching persona:', error);
            alert('Error switching persona. Please try again.');
        });
    }
    
    /**
     * Get CSRF token from meta tag or cookie
     */
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        // Fallback: try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
});
