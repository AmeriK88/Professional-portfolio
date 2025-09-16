(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var alerts = document.querySelectorAll('.js-animated-message');

    alerts.forEach(function (el, i) {
      // 1) entrada con retardo escalonado
      setTimeout(function () {
        el.classList.add('show'); // activa la transición de Bootstrap (fade)
      }, 100 + i * 80);

      // 2) autocierre opcional
      var ms = parseInt(el.getAttribute('data-autoclose') || '0', 10);
      if (ms > 0) {
        setTimeout(function () {
          try {
            var inst = bootstrap.Alert.getOrCreateInstance(el);
            inst.close();
          } catch (_) {}
        }, ms + 250); // un pelín después de la animación de entrada
      }
    });
  });
})();
