/**
 * GRN PROPERTIES - Theme Management Engine
 * Handles instant client-side switching, zero-FOUC persistence, and server sync.
 */

(function () {
  const THEMES = {
    'luxury-gold': { label: 'Signature Gold', desc: 'Signature Gold & Warm Pearl' },
    'sapphire-blue': { label: 'Sapphire Royal', desc: 'Ocean Royal & Clean Blue' },
    'emerald-green': { label: 'Emerald Prestige', desc: 'Forest Jade & Mint Light' },
    'amethyst-purple': { label: 'Velvet Amethyst', desc: 'Regal Plum & Lavender Light' },
    'executive-light': { label: 'Platinum Pearl', desc: 'Clean Modern Light Slate' },
    'midnight-ivory': { label: 'Midnight & Ivory', desc: 'Warm Ivory & Champagne Gold' }
  };

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};path=/;max-age=${days * 86400};SameSite=Lax`;
  }

  function getInitialTheme() {
    return localStorage.getItem('grn_theme') || getCookie('grn_theme') || document.documentElement.getAttribute('data-theme') || 'luxury-gold';
  }

  window.applyGRNTheme = function (themeName, shouldSyncServer = true) {
    if (!THEMES[themeName]) {
      themeName = 'luxury-gold';
    }

    // 1. Apply to DOM immediately
    document.documentElement.setAttribute('data-theme', themeName);

    // 2. Persist in localStorage & cookie
    try {
      localStorage.setItem('grn_theme', themeName);
    } catch (e) {
      // Storage access blocked or quota exceeded
    }
    setCookie('grn_theme', themeName, 365);

    // 3. Update active UI elements
    updateThemeUI(themeName);

    // 4. Synchronize with server if requested
    if (shouldSyncServer) {
      fetch('/api/set-theme', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ theme: themeName })
      }).catch(() => {
        // Silent catch for offline or non-blocking network error
      });
    }
  };

  function updateThemeUI(themeName) {
    const themeInfo = THEMES[themeName] || THEMES['luxury-gold'];

    // Update theme label text in buttons
    document.querySelectorAll('.theme-active-label').forEach(el => {
      el.textContent = themeInfo.label;
    });

    // Update active state in theme choices
    document.querySelectorAll('.theme-choice').forEach(btn => {
      const val = btn.getAttribute('data-theme-value');
      const checkIcon = btn.querySelector('.theme-check');
      if (val === themeName) {
        btn.classList.add('active');
        if (checkIcon) checkIcon.classList.remove('d-none');
      } else {
        btn.classList.remove('active');
        if (checkIcon) checkIcon.classList.add('d-none');
      }
    });
  }

  // Pre-apply theme immediately to avoid flash
  const initialTheme = getInitialTheme();
  document.documentElement.setAttribute('data-theme', initialTheme);

  // Initialize theme UI once DOM is loaded
  document.addEventListener('DOMContentLoaded', function () {
    const currentTheme = getInitialTheme();
    updateThemeUI(currentTheme);

    // Delegate theme switch clicks
    document.addEventListener('click', function (e) {
      const choiceBtn = e.target.closest('.theme-choice');
      if (choiceBtn) {
        e.preventDefault();
        const selectedTheme = choiceBtn.getAttribute('data-theme-value');
        if (selectedTheme) {
          window.applyGRNTheme(selectedTheme, true);
        }
      }
    });
  });
})();

