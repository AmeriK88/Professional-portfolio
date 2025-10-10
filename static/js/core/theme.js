(function () {
  const KEY = 'theme';            
  const root = document.documentElement;
  const themeMeta = document.querySelector('meta[name="theme-color"]');
  const icon = document.getElementById('theme-toggle-icon');
  const btn = document.getElementById('theme-toggle');
  const logo = document.getElementById('brand-logo'); 

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function currentTheme() {
    const stored = localStorage.getItem(KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function swapLogoForTheme(theme) {
    if (!logo) return;
    const light = logo.getAttribute('data-light');
    const dark  = logo.getAttribute('data-dark');
    const next  = (theme === 'dark') ? dark : light;
    if (next && logo.getAttribute('src') !== next) {
      logo.setAttribute('src', next);
    }
  }

  function applyTheme(t) {
    root.setAttribute('data-bs-theme', t);

    // Actualiza barra de navegador en móviles
    if (themeMeta) {
      themeMeta.setAttribute('content', t === 'dark' ? '#0b0f14' : '#0d6efd');
    }

    // Icono del botón
    if (icon) {
      icon.className = t === 'dark' ? 'fa-regular fa-sun' : 'fa-regular fa-moon';
    }

    // Logo según tema
    swapLogoForTheme(t);
  }

  // Inicial
  applyTheme(currentTheme());

  // Responder a cambios del sistema si el user no fijó nada
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  media.addEventListener?.('change', () => {
    const stored = localStorage.getItem(KEY);
    if (!stored) applyTheme(currentTheme());
  });

  // Toggle manual
  if (btn) {
    btn.addEventListener('click', () => {
      const next = (currentTheme() === 'dark') ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      applyTheme(next);
    });
  }
})();
