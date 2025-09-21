(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var bar   = document.getElementById('redir-bar');
    var msg   = document.getElementById('redir-msg');
    var goNow = document.getElementById('go-now');
    var stay  = document.getElementById('stay-here');

    if (!goNow) return; // no hay nada que hacer si no existe el objetivo

    var target   = goNow.getAttribute('href');
    var root     = document.getElementById('redir-root') || document.body;
    var duration = parseInt(root.getAttribute('data-duration') || '3000', 10);

    // Respeta usuarios que prefieran menos movimiento
    var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) duration = Math.min(duration, 800);

    var start = Date.now();
    var cancelled = false;

    function tick() {
      if (cancelled) return;
      var elapsed = Date.now() - start;
      var pct = Math.min(100, (elapsed / duration) * 100);
      if (bar) bar.style.width = pct.toFixed(0) + '%';
      if (elapsed >= duration) {
        window.location.href = target;
        return;
      }
      requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
    var timer = setTimeout(function () {
      if (!cancelled) window.location.href = target;
    }, duration + 150);

    if (stay) {
      stay.addEventListener('click', function () {
        cancelled = true;
        clearTimeout(timer);
        if (msg) msg.textContent = 'Autoredirección cancelada.';
        if (bar) {
          bar.classList.remove('progress-bar-animated');
          bar.classList.remove('progress-bar-striped');
        }
      });
    }

    goNow.addEventListener('click', function () {
      cancelled = true;
      clearTimeout(timer);
    });
  });
})();
