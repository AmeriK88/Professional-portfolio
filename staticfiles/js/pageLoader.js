(function () {
  'use strict';

  var loader = null;
  var showTimer = null;
  var pending = false;

  function ensureLoader() {
    if (!loader) loader = document.getElementById('page-loader');
    return !!loader;
  }

  function showDelayed() {
    if (!ensureLoader() || pending) return;
    pending = true;
    // Evita “flash” en navegaciones ultra rápidas
    showTimer = setTimeout(function () {
      if (!loader) return;
      loader.classList.add('active');
      loader.setAttribute('aria-hidden', 'false');
    }, 120);
  }

  function hide() {
    if (!ensureLoader()) return;
    pending = false;
    clearTimeout(showTimer);
    loader.classList.remove('active');
    loader.setAttribute('aria-hidden', 'true');
  }

  // Oculta al entrar en una página (incluido back/forward cache)
  window.addEventListener('DOMContentLoaded', hide);
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) hide();
  });

  // IMPORTANTE: ocultar loader en navegación por hash (misma página)
  window.addEventListener('hashchange', hide);

  // Enlaces: muestra loader en navegaciones válidas (mismo origen, sin #, sin _blank, sin download)
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;

    // Opt-out manual
    if (a.hasAttribute('data-no-loader') || a.classList.contains('no-loader')) return;

    var href = a.getAttribute('href');
    if (!href) return;

    // Si es hash puro (#id), jamás mostramos loader
    if (href.charAt(0) === '#') return;

    // Respeta enlaces que abren nueva pestaña o descarga
    if (a.target && a.target !== '' && a.target !== '_self') return;
    if (a.hasAttribute('download')) return;

    // Sólo mismo origen (no bloqueamos navegación externa)
    var url;
    try {
      url = new URL(href, window.location.href);
    } catch (err) {
      return; // href relativo raro: mejor no intervenir
    }
    if (url.origin !== window.location.origin) return;

    // --- NUEVO: si solo cambia el hash (misma ruta y query), NO mostramos loader ---
    var norm = function (p) { return p.replace(/\/+$/, ''); }; // quita barra final
    var samePath   = norm(url.pathname) === norm(window.location.pathname);
    var sameSearch = url.search === window.location.search;
    var isHashNav  = !!url.hash && samePath && sameSearch;
    if (isHashNav) return;

    showDelayed();
    // No prevenimos el click: dejamos que el navegador navegue con normalidad
  }, { capture: true });

  // Formularios: muestra loader en submit (a menos que se pida lo contrario)
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (form.matches('[data-no-loader]')) return;
    showDelayed();
  }, { capture: true });

  // Fallback: beforeunload (algunas navegaciones no disparan click/submit)
  window.addEventListener('beforeunload', function () {
    showDelayed();
  });

  // API pública por si quieres controlar manualmente en alguna vista
  window.PageLoader = { show: showDelayed, hide: hide };
})();
