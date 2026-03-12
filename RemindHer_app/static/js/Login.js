document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('signinForm');
    const errorMessage = document.getElementById('errorMessage');
    const submitButton = document.getElementById('submitButton');
    const googleButton = document.getElementById('googleLogin');
    const facebookButton = document.getElementById('facebookLogin');

    // Form submission - let it submit normally to Django
    form.addEventListener('submit', () => {
        submitButton.disabled = true;
        submitButton.textContent = 'Signing in...';
    });

    // Social login handlers - show message for now
    googleButton.addEventListener('click', () => {
        alert('Google login is not configured. Please use email login.');
    });

    facebookButton.addEventListener('click', () => {
        alert('Facebook login is not configured. Please use email login.');
    });
});
