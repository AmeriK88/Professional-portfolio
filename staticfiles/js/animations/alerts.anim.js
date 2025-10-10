(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var alerts = document.querySelectorAll('.js-animated-message');

    alerts.forEach(function (el, i) {
      // 1) Animation activation bootstrap class
      setTimeout(function () {
        el.classList.add('show'); 
      }, 100 + i * 80);

      // 2) Autoclose functionality
      var ms = parseInt(el.getAttribute('data-autoclose') || '0', 10);
      if (ms > 0) {
        setTimeout(function () {
          try {
            var inst = bootstrap.Alert.getOrCreateInstance(el);
            inst.close();
          } catch (_) {}
        }, ms + 250); 
      }
    });
  });
})();
