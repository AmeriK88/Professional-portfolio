(function () {
  const qs = new URLSearchParams(location.search);
  const DEBUG = qs.has('debug') || localStorage.getItem('pi.debug') === '1';
  const log = (...a) => DEBUG && console.log('[pi-login]', ...a);

  function getCsrf(name = 'csrftoken') {
    return document.cookie.split('; ').find(r => r.startsWith(name + '='))?.split('=')[1];
  }

  function showMsg(text, type = 'info') {
    let box = document.getElementById('pi-login-msg');
    if (!box) {
      box = document.createElement('div');
      box.id = 'pi-login-msg';
      box.className = 'mt-2 small';
      const btn = document.getElementById('btn-pi-login');
      if (btn && btn.parentNode) btn.parentNode.appendChild(box);
    }
    box.className = `mt-2 small text-${type}`;
    box.textContent = text;
  }

  // Autenticación ÚNICA con fallback y timeout
  async function authenticateOnce({ timeoutMs = 25000 } = {}) {
    if (!window.__isPiEnv || !window.Pi || typeof window.Pi.authenticate !== 'function') {
      throw new Error('pi-sdk-not-ready');
    }

    const timeout = new Promise((_, rej) =>
      setTimeout(() => rej(new Error('authenticate-timeout')), timeoutMs)
    );

    // Primer intento (permiso mínimo para login)
    try {
      log('auth try: ["username"]');
      return await Promise.race([window.Pi.authenticate(['username']), timeout]);
    } catch (e1) {
      log('auth ["username"] failed:', e1);
      // Segundo intento (si quisieras ampliar permisos en futuro, cámbialo aquí)
      log('auth fallback: ["username"]');
      return await Promise.race([window.Pi.authenticate(['username']), timeout]);
    }
  }

  async function onClick(btn) {
    try {
      if (!window.__isPiEnv || !window.Pi) {
        showMsg('Open this page in Pi Browser to sign in', 'danger');
        return;
      }
      if (typeof window.Pi.authenticate !== 'function') {
        showMsg('Pi SDK not ready. Reload in Pi Browser', 'danger');
        log('Pi object', window.Pi);
        return;
      }

      btn.disabled = true;
      const originalText = btn.textContent;
      btn.textContent = 'Conectando con Pi…';
      showMsg('Esperando autorización en Pi Browser…', 'muted');

      // Autenticación única (con timeout y fallback interno)
      const { accessToken } = await authenticateOnce({ timeoutMs: 25000 });
      if (!accessToken) throw new Error('no-access-token');

      // POST al backend
      const postUrl = btn.dataset.loginUrl;
      const redirectUrl = btn.dataset.redirectUrl;

      const resp = await fetch(postUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({ accessToken }),
        credentials: 'same-origin'
      });

      if (!resp.ok) {
        const body = await resp.text().catch(() => '');
        if (resp.status === 403) throw new Error('csrf-or-forbidden');
        throw new Error(`pi_login-failed: ${resp.status} ${body.slice(0, 200)}`);
      }

      showMsg('Sesión iniciada. Redirigiendo…', 'success');
      const next = new URLSearchParams(location.search).get('next');
      location.href = next || redirectUrl || '/';

    } catch (e) {
      log('onClick error:', e);
      const emsg = String(e?.message || e).toLowerCase();
      if (emsg.includes('authenticate-timeout')) {
        showMsg('La autorización tardó demasiado. Reintenta en Pi Browser.', 'danger');
      } else if (emsg.includes('csrf') || emsg.includes('forbidden')) {
        showMsg('No se pudo validar la sesión (CSRF). Actualiza la página e inténtalo de nuevo.', 'danger');
      } else if (emsg.includes('pi-sdk-not-ready')) {
        showMsg('Pi SDK no está listo. Abre en Pi Browser y recarga.', 'danger');
      } else {
        showMsg('No se pudo iniciar sesión con Pi. Autoriza el Sandbox y reintenta.', 'danger');
      }
    } finally {
      const b = document.getElementById('btn-pi-login');
      if (b) { b.disabled = false; b.textContent = 'Iniciar sesión con Pi'; }
    }
  }

  function bindIfReady() {
    const btn = document.getElementById('btn-pi-login');
    if (!btn) { log('no #btn-pi-login on page'); return; }

    if (!window.__isPiEnv || !window.Pi || typeof window.Pi.authenticate !== 'function') {
      btn.disabled = true;
      btn.title = 'Open this page in Pi Browser to sign in';
      showMsg('Abre esta página en Pi Browser para continuar.', 'muted');
      log('disabled outside Pi env', { __isPiEnv: window.__isPiEnv, Pi: !!window.Pi });
      return;
    }

    if (btn.dataset.bound === '1') return;
    btn.dataset.bound = '1';
    btn.disabled = false;
    btn.addEventListener('click', () => onClick(btn));
    log('click handler bound');
  }

  function setup() {
    // pequeño backoff por si el SDK llega un pelo tarde aunque haya pi:ready
    let attempts = 0;
    const tick = () => {
      bindIfReady();
      if ((!window.Pi || typeof window.Pi.authenticate !== 'function') && attempts < 50) {
        attempts++; setTimeout(tick, 120);
      }
    };
    tick();
    document.addEventListener('pi:ready', () => { attempts = 0; tick(); }, { once: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
