
(function () {
  'use strict';

  const qs = new URLSearchParams(window.location.search);

  let debugEnabled = qs.has('debug');

  try {
    debugEnabled =
      debugEnabled ||
      localStorage.getItem('pi.debug') === '1';
  } catch (_) {
    // El almacenamiento puede estar restringido.
  }

  const DEBUG = debugEnabled;

  const log = (...args) => {
    if (DEBUG) {
      console.log('[pi-login]', ...args);
    }
  };

  // --------------------------------------------------
  // Helpers
  // --------------------------------------------------

  function getCsrf(name = 'csrftoken') {
    return document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='))
      ?.split('=')
      .slice(1)
      .join('');
  }

  function showMsg(text, type = 'info') {
    let box = document.getElementById('pi-login-msg');

    if (!box) {
      box = document.createElement('div');
      box.id = 'pi-login-msg';

      const btn = document.getElementById('btn-pi-login');

      if (btn && btn.parentNode) {
        btn.parentNode.appendChild(box);
      }
    }

    box.className = `mt-2 small text-${type}`;
    box.textContent = text;
  }

  // --------------------------------------------------
  // Esperar a que pi-init.js inicialice el SDK
  // --------------------------------------------------

  async function ensurePiReady() {
    if (!window.__piInitPromise) {
      log('No existe __piInitPromise');
      return false;
    }

    try {
      const ready = await window.__piInitPromise;

      return (
        ready === true &&
        window.__isPiEnv === true &&
        !!window.Pi &&
        typeof window.Pi.authenticate === 'function'
      );
    } catch (error) {
      log('Error esperando Pi SDK:', error);
      return false;
    }
  }

  // --------------------------------------------------
  // Autenticación con Pi
  // --------------------------------------------------

  async function authenticateOnce({
    timeoutMs = 25000
  } = {}) {
    const ready = await ensurePiReady();

    if (!ready) {
      throw new Error('pi-sdk-not-ready');
    }

    log('Solicitando permiso ["username"]');

    let timeoutId;

    const timeout = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error('authenticate-timeout'));
      }, timeoutMs);
    });

    try {
      return await Promise.race([
        window.Pi.authenticate(['username']),
        timeout
      ]);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // --------------------------------------------------
  // Evento del botón
  // --------------------------------------------------

  async function onClick(btn) {
    if (btn.disabled) {
      return;
    }

    const originalText = btn.textContent;

    btn.disabled = true;

    try {
      btn.textContent = 'Conectando con Pi...';

      showMsg(
        'Comprobando conexión con Pi Browser...',
        'muted'
      );

      const ready = await ensurePiReady();

      if (!ready) {
        throw new Error('pi-sdk-not-ready');
      }

      showMsg(
        'Esperando autorización en Pi Browser...',
        'muted'
      );

      // 1. Autenticación con Pi.
      const auth = await authenticateOnce({
        timeoutMs: 25000
      });

      const accessToken = auth?.accessToken;

      if (!accessToken) {
        throw new Error('no-access-token');
      }

      // 2. Enviar token al backend Django.
      const postUrl = btn.dataset.loginUrl;
      const redirectUrl = btn.dataset.redirectUrl;

      if (!postUrl) {
        throw new Error('missing-login-url');
      }

      const response = await fetch(postUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf() || ''
        },
        body: JSON.stringify({
          accessToken
        })
      });

      if (!response.ok) {
        const body = await response
          .text()
          .catch(() => '');

        if (response.status === 403) {
          throw new Error('csrf-or-forbidden');
        }

        throw new Error(
          `pi_login-failed: ${response.status} ${body.slice(0, 200)}`
        );
      }

      // 3. Inicio de sesión correcto.
      showMsg(
        'Sesión iniciada. Redirigiendo...',
        'success'
      );

      const next = new URLSearchParams(
        window.location.search
      ).get('next');

      // Solo permitir redirecciones relativas internas.
      const destination =
        next && next.startsWith('/') && !next.startsWith('//')
          ? next
          : redirectUrl || '/';

      window.location.assign(destination);

    } catch (error) {
      log('onClick error:', error);

      const message = String(
        error?.message || error
      ).toLowerCase();

      if (message.includes('authenticate-timeout')) {
        showMsg(
          'La autorización tardó demasiado. Reintenta en Pi Browser.',
          'danger'
        );
      } else if (
        message.includes('csrf') ||
        message.includes('forbidden')
      ) {
        showMsg(
          'No se pudo validar la sesión (CSRF). Actualiza la página e inténtalo de nuevo.',
          'danger'
        );
      } else if (message.includes('pi-sdk-not-ready')) {
        showMsg(
          'Pi SDK no está listo. Abre esta página en Pi Browser y recarga.',
          'danger'
        );
      } else {
        showMsg(
          'No se pudo iniciar sesión con Pi. Comprueba la autorización e inténtalo de nuevo.',
          'danger'
        );
      }
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  // --------------------------------------------------
  // Inicializar botón de login
  // --------------------------------------------------

  async function setup() {
    const btn = document.getElementById(
      'btn-pi-login'
    );

    if (!btn) {
      log('No existe #btn-pi-login');
      return;
    }

    if (btn.dataset.bound === '1') {
      return;
    }

    btn.dataset.bound = '1';
    btn.disabled = true;

    showMsg(
      'Comprobando disponibilidad de Pi Browser...',
      'muted'
    );

    // Esperar a que termine la inicialización.
    const ready = await ensurePiReady();

    if (!ready) {
      btn.disabled = true;

      btn.title =
        'Abre esta página en Pi Browser para iniciar sesión';

      showMsg(
        'Abre esta página en Pi Browser para continuar.',
        'muted'
      );

      log('Pi SDK no disponible');
      return;
    }

    btn.disabled = false;
    btn.title = '';

    btn.addEventListener('click', () => {
      onClick(btn);
    });

    log('Botón de login Pi preparado');
  }

  if (document.readyState === 'loading') {
    document.addEventListener(
      'DOMContentLoaded',
      setup
    );
  } else {
    setup();
  }
})();
