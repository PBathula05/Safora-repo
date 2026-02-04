/**
 * Displays a custom message box at the top of the screen.
 * The message box fades out after 3 seconds.
 * @param {string} message - The message to display.
 */
function showMessageBox(message) {
    let messageBox = document.getElementById('customMessageBox');
    if (!messageBox) {
        messageBox = document.createElement('div');
        messageBox.id = 'customMessageBox';
        messageBox.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
            font-family: 'Roboto', sans-serif;
            font-size: 16px;
        `;
        document.body.appendChild(messageBox);
    }
    messageBox.textContent = message;
    messageBox.style.opacity = '1';

    setTimeout(() => {
        messageBox.style.opacity = '0';
    }, 3000); // Message disappears after 3 seconds
}

/**
 * Toggles dark mode on and off.
 * Stores the preference in localStorage.
 */
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    // Save user preference
    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Apply saved theme preference on load
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        // Default to light if no preference or explicitly set to light
        document.body.classList.remove('dark-mode');
    }

    // Attach dark mode toggle listener
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }

    // Navigation active state logic
    const navLinks = document.querySelectorAll('.nav-links a, .header-nav a, .nav ul li a');
    const currentPath = window.location.pathname.split('/').pop();

    navLinks.forEach(link => {
        let linkHref = link.getAttribute('href');
        // Skip links without an href or purely anchor links
        if (!linkHref || linkHref === '#') return;

        let linkPath = linkHref.split('/').pop();

        // Normalize currentPath for comparison: empty path for root, 'index.html' for '/'
        const actualCurrentPath = currentPath === '' ? 'index.html' : currentPath;

        // Check for active state based on exact match or special home/index handling
        if (linkPath === actualCurrentPath ||
            (linkPath === 'home.html' && actualCurrentPath === 'index.html') ||
            (linkPath === 'index.html' && actualCurrentPath === 'home.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // You can add more global JavaScript functionality here as needed.
});