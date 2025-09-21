/* cookiesConsent.portfolio.js — Minimal external-services consent for portfolio */
(function () {
  const KEY = 'ck-consent-v1';
  const firstLayerEl = document.getElementById('ck-modal');
  const firstLayer   = () => firstLayerEl ? bootstrap.Modal.getOrCreateInstance(firstLayerEl, { backdrop: 'static', keyboard: false }) : null;
  const panelEl = document.getElementById('ck-panel');
  const panel   = () => bootstrap.Modal.getOrCreateInstance(panelEl);
  const extEl   = document.getElementById('ext-modal');
  const extModal= () => bootstrap.Modal.getOrCreateInstance(extEl);

  const q = (s) => document.querySelector(s);
  const getVersion = () => document.querySelector('meta[name="application-version"]')?.content || '1.0';

  const defaultConsent = () => ({
    necessary: true,
    external: false, // allow opening external services without prompt
    ts: new Date().toISOString(),
    version: getVersion()
  });

  const readConsent = () => {
    try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; }
  };
  const saveConsent = (obj) => {
    const data = { ...defaultConsent(), ...obj, ts: new Date().toISOString(), version: getVersion() };
    localStorage.setItem(KEY, JSON.stringify(data));
    return data;
  };

  // First layer
  const showFirstLayerIfNeeded = () => {
    if (!readConsent()) firstLayer()?.show();
  };

  // Open preferences
  const openPanel = (e) => {
    e?.preventDefault?.();
    const c = readConsent() || defaultConsent();
    const sw = q('#ck-external'); if (sw) sw.checked = !!c.external;
    panel().show();
  };

  // External links interception
  const EXTERNAL_HOSTS = ['wa.me', 'api.whatsapp.com', 'linkedin.com', 'www.linkedin.com', 'github.com', 'www.github.com'];
  let lastHref = null;

  const isExternalTarget = (a) => {
    try {
      const url = new URL(a.href, window.location.href);
      return EXTERNAL_HOSTS.includes(url.host) || a.hasAttribute('data-external');
    } catch { return false; }
  };

  document.addEventListener('click', (e) => {
    const openBtn = e.target.closest('[data-ck-open]');
    if (openBtn) return openPanel(e);

    const a = e.target.closest('a[href]');
    if (!a) return;

    if (!isExternalTarget(a)) return;

    const consent = readConsent() || defaultConsent();
    if (consent.external) return; // allow as normal

    // intercept and show external confirm
    e.preventDefault();
    lastHref = a.href;
    const host = (() => { try { return new URL(a.href).host; } catch { return a.href; } })();
    q('#ext-host').textContent = host;
    q('#ext-remember').checked = false;
    q('#ext-continue').disabled = true;
    extModal().show();
  });

  // External modal controls
  q('#ext-remember')?.addEventListener('change', (e) => {
    q('#ext-continue').disabled = !e.target.checked;
  });
  q('#ext-continue')?.addEventListener('click', () => {
    const remember = q('#ext-remember')?.checked;
    if (remember) {
      const c = readConsent() || defaultConsent();
      c.external = true;
      saveConsent(c);
    }
    const href = lastHref;
    lastHref = null;
    extModal().hide();
    if (href) window.open(href, '_blank', 'noopener');
  });

  // First layer buttons
  q('#ck-accept')?.addEventListener('click', () => {
    saveConsent({ external: true });
    firstLayer()?.hide();
  });
  q('#ck-reject')?.addEventListener('click', () => {
    saveConsent({ external: false });
    firstLayer()?.hide();
  });

  // Panel save
  q('#ck-save')?.addEventListener('click', () => {
    const c = readConsent() || defaultConsent();
    c.external = !!q('#ck-external')?.checked;
    saveConsent(c);
    panel().hide();
  });

  // Init
  document.addEventListener('DOMContentLoaded', () => {
    showFirstLayerIfNeeded();
  });
})();
