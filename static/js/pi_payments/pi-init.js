(function initPi() {
  if (window.__piInitDone) return;
  window.__piInitDone = true;

  const ua = (navigator.userAgent || '').toLowerCase();
  const isPiBrowserUA = ua.includes('pibrowser');
  const ref = document.referrer || '';
  const fromSandboxRef = /sandbox\.minepi\.com/i.test(ref);
  const ancestorSandbox = (() => {
    try {
      const ao = (location.ancestorOrigins || []);
      for (let i = 0; i < ao.length; i++) if (/sandbox\.minepi\.com/i.test(ao[i])) return true;
    } catch (_) {}
    return false;
  })();

  const qs = new URLSearchParams(location.search);
  const forceInit = qs.has('pi_force_init') || localStorage.getItem('pi.forceInit') === '1';
  const isPiEnv = forceInit || isPiBrowserUA || fromSandboxRef || ancestorSandbox;
  window.__isPiEnv = isPiEnv;

  const fireReady = () => document.dispatchEvent(new Event('pi:ready'));

  // Si no es entorno Pi, no intentes init; pero permite que el resto sepa que "ya terminó"
  if (!isPiEnv) { console.warn('Pi SDK: non-Pi env; skipping Pi.init'); fireReady(); return; }

  // Espera activa a que el SDK esté presente antes de inicializar
  let tries = 0, maxTries = 60; // ~6s si interval=100ms
  const interval = setInterval(() => {
    tries++;
    if (window.Pi && typeof window.Pi.init === 'function') {
      clearInterval(interval);
      try {
        window.Pi.init({ version: '2.0', sandbox: true }); // clave en sandbox
      } catch (e) {
        console.warn('Pi.init failed (continuing)', e);
      } finally {
        fireReady();
      }
    } else if (tries >= maxTries) {
      clearInterval(interval);
      console.warn('Pi SDK not loaded in time');
      fireReady(); // permite que UI muestre instrucciones
    }
  }, 100);
})();
