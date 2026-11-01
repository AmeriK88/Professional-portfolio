
(function initPi() {
  'use strict';
  const cfg = window.PI_CFG || {};

  // Evitar inicializaciones duplicadas.
  if (window.__piInitPromise) {
    return;
  }

  // --------------------------------------------------
  // 1. Detectar entorno Pi Browser / Sandbox
  // --------------------------------------------------

  const ua = (navigator.userAgent || '').toLowerCase();
  const isPiBrowserUA = ua.includes('pibrowser');

  const referrer = document.referrer || '';

  const fromSandboxRef =
    /sandbox\.minepi\.com/i.test(referrer);

  let ancestorSandbox = false;

  try {
    const origins = window.location.ancestorOrigins || [];

    ancestorSandbox = Array.from(origins).some(origin =>
      /sandbox\.minepi\.com/i.test(origin)
    );
  } catch (error) {
    // Algunos navegadores no exponen ancestorOrigins.
  }

  // Permitir forzar la detección para pruebas.
  const qs = new URLSearchParams(window.location.search);

  let forceInit = qs.has('pi_force_init');

  try {
    forceInit =
      forceInit ||
      localStorage.getItem('pi.forceInit') === '1';
  } catch (error) {
    // localStorage puede estar restringido.
  }

  const isPiEnv =
    isPiBrowserUA ||
    fromSandboxRef ||
    ancestorSandbox ||
    forceInit;

  window.__isPiEnv = isPiEnv;

  // --------------------------------------------------
  // 2. Estado global de inicialización
  // --------------------------------------------------

  window.__piInitDone = false;
  window.__PI_INIT_DONE__ = false;

  const fireReady = () => {
    document.dispatchEvent(new Event('pi:ready'));
  };

  // --------------------------------------------------
  // 3. Crear promesa compartida de inicialización
  // --------------------------------------------------

  window.__piInitPromise = new Promise(resolve => {

    if (!isPiEnv) {
      console.warn(
        '[Pi SDK] Entorno Pi no detectado. ' +
        'No se inicializará el SDK.'
      );

      fireReady();
      resolve(false);
      return;
    }

    let attempts = 0;
    const maxAttempts = 60;
    const intervalMs = 100;

    const interval = setInterval(() => {
      attempts++;

      // Esperar a que el SDK oficial esté disponible.
      if (
        window.Pi &&
        typeof window.Pi.init === 'function'
      ) {
        clearInterval(interval);

        try {
          // Inicializar SDK una sola vez.
          window.Pi.init({
            version: '2.0',
            sandbox: Boolean(cfg.sandbox),
          });

          // Verificar que la API de autenticación existe.
          if (
            typeof window.Pi.authenticate !== 'function'
          ) {
            throw new Error(
              'Pi.authenticate no está disponible'
            );
          }

          // Inicialización completada.
          window.__piInitDone = true;
          window.__PI_INIT_DONE__ = true;

          console.info(
            '[Pi SDK] Inicialización completada correctamente.'
          );

          fireReady();
          resolve(true);

        } catch (error) {
          console.error(
            '[Pi SDK] Error durante Pi.init():',
            error
          );

          window.__piInitDone = false;
          window.__PI_INIT_DONE__ = false;

          fireReady();
          resolve(false);
        }

        return;
      }

      // SDK no disponible después de 6 segundos.
      if (attempts >= maxAttempts) {
        clearInterval(interval);

        console.error(
          '[Pi SDK] No se pudo cargar el SDK ' +
          'después de 6 segundos.'
        );

        window.__piInitDone = false;
        window.__PI_INIT_DONE__ = false;

        fireReady();
        resolve(false);
      }

    }, intervalMs);
  });

})();
