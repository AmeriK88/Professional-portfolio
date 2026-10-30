
(function () {
  'use strict';

  // Evita registrar los eventos dos veces.
  if (window.__PI_PAY_INIT__) return;
  window.__PI_PAY_INIT__ = true;

  const cfg = window.PI_CFG || {};

  console.debug('[pi] pi_payments.js cargado');

  // --------------------------------------------------
  // Helpers
  // --------------------------------------------------

  function getCookie(name) {
    const m = document.cookie.match(
      '(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'
    );

    return m ? m.pop() : '';
  }

  const csrftoken = getCookie('csrftoken');

  // --------------------------------------------------
  // Entorno seguro y disponibilidad del SDK
  // --------------------------------------------------

  function isSecurePublicContext() {
    const isHttps = location.protocol === 'https:';

    const isLocal = /^(localhost|127\.0\.0\.1)$/i.test(
      location.hostname
    );

    return isHttps && !isLocal;
  }

  // Pi.init() se ejecuta exclusivamente en pi-init.js.
  // Aquí esperamos a que termine su inicialización.

  async function ensurePiReady() {
    if (!isSecurePublicContext()) {
      console.warn('[pi] Se requiere HTTPS público');
      return false;
    }

    if (!window.__piInitPromise) {
      console.error('[pi] No se ha cargado pi-init.js');
      return false;
    }

    try {
      const ready = await window.__piInitPromise;

      return ready === true && !!window.Pi;
    } catch (error) {
      console.error(
        '[pi] Falló la inicialización',
        error
      );

      return false;
    }
  }

  // --------------------------------------------------
  // Comunicación con Django
  // --------------------------------------------------

  async function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || '',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(body || {})
    });
  }

  // --------------------------------------------------
  // Checkout
  // --------------------------------------------------

  async function startCheckout(checkoutUrl) {
    if (!checkoutUrl) {
      throw new Error(
        'No se definió data-checkout-url en el botón.'
      );
    }

    const res = await postJSON(checkoutUrl, {});

    // Si Django redirige al login, seguimos la redirección.
    if (
      res.redirected ||
      (res.url && res.url.includes('/login'))
    ) {
      window.location.href =
        res.url ||
        ('/login/?next=' + window.location.pathname);

      return null;
    }

    if (!res.ok) {
      throw new Error('No se pudo iniciar el pedido.');
    }

    const data = await res.json();

    if (!data.ok || !data.payment) {
      throw new Error(
        'Respuesta de checkout inválida.'
      );
    }

    return data;
  }

  // --------------------------------------------------
  // Autenticación y permiso de pagos
  // --------------------------------------------------

  let paymentsAuthPromise = null;

  async function ensurePaymentsScope() {
    if (!(await ensurePiReady())) {
      return false;
    }

    if (!paymentsAuthPromise) {
      const onIncompletePaymentFound = async (payment) => {
        try {
          console.debug(
            '[pi] incomplete payment found',
            payment
          );

          const pid =
            payment?.identifier ||
            payment?.paymentId ||
            payment?.id;

          const txid = payment?.transaction?.txid;

          if (pid && txid) {
            if (cfg.completeUrl) {
              await postJSON(cfg.completeUrl, {
                paymentId: pid,
                txid
              });
            }
          } else if (pid) {
            if (cfg.approveUrl) {
              await postJSON(cfg.approveUrl, {
                paymentId: pid
              });
            }
          }
        } catch (error) {
          console.error(
            '[pi] onIncompletePaymentFound error',
            error
          );
        }
      };

      paymentsAuthPromise = window.Pi
        .authenticate(
          ['payments'],
          onIncompletePaymentFound
        )
        .then(() => true)
        .catch(error => {
          console.error(
            '[pi] authenticate error',
            error
          );

          paymentsAuthPromise = null;

          return false;
        });
    }

    return paymentsAuthPromise;
  }

  // --------------------------------------------------
  // Crear pago
  // --------------------------------------------------

  async function createPayment(paymentPayload) {
    const {
      approveUrl,
      completeUrl,
      cancelUrl,
      successUrl
    } = cfg;

    if (!approveUrl || !completeUrl || !cancelUrl) {
      throw new Error(
        'Faltan URLs de callbacks de Pi en PI_CFG.'
      );
    }

    const authed = await ensurePaymentsScope();

    if (!authed) {
      throw new Error(
        'Debes autorizar el permiso de pagos de Pi para continuar.'
      );
    }

    return new Promise((resolve, reject) => {
      try {
        window.Pi.createPayment(paymentPayload, {
          onReadyForServerApproval: async (paymentId) => {
            console.debug(
              '[pi] onReadyForServerApproval',
              paymentId
            );

            try {
              const response = await postJSON(
                approveUrl,
                { paymentId }
              );

              if (!response.ok) {
                throw new Error(
                  'Fallo aprobando en servidor'
                );
              }
            } catch (error) {
              console.error(error);

              alert(
                'Error aprobando el pago. Intenta de nuevo.'
              );
            }
          },

          onReadyForServerCompletion: async (
            paymentId,
            txid
          ) => {
            console.debug(
              '[pi] onReadyForServerCompletion',
              paymentId,
              txid
            );

            try {
              const response = await postJSON(
                completeUrl,
                { paymentId, txid }
              );

              if (response.ok) {
                const base = successUrl || '/';

                const url = new URL(
                  base,
                  window.location.origin
                );

                url.searchParams.set(
                  'pid',
                  paymentId
                );

                window.location.assign(
                  url.toString()
                );

                resolve({ paymentId, txid });
              } else {
                alert(
                  'No se pudo completar el pago en el servidor.'
                );

                reject(
                  new Error('complete failed')
                );
              }
            } catch (error) {
              console.error(error);

              alert(
                'Error completando el pago.'
              );

              reject(error);
            }
          },

          onCancel: async (paymentId) => {
            console.debug(
              '[pi] onCancel',
              paymentId
            );

            try {
              await postJSON(
                cancelUrl,
                { paymentId }
              );
            } catch (error) {
              console.error(
                '[pi] Error notificando cancelación',
                error
              );
            }

            // La cancelación es una acción del usuario.
          },

          onError: (error, payment) => {
            console.error(
              '[pi] onError',
              error,
              payment
            );

            alert(
              'Ha ocurrido un error con Pi. Reintenta en unos segundos.'
            );

            reject(error);
          }
        });
      } catch (error) {
        console.error(
          '[pi] createPayment falló',
          error
        );

        if (
          String(error?.message || error)
            .includes('payments')
        ) {
          alert(
            'No se pudo crear el pago porque falta el permiso de pagos. Autorízalo y reintenta.'
          );
        } else {
          alert(
            'No se pudo crear el pago. Intenta de nuevo.'
          );
        }

        reject(error);
      }
    });
  }

  // --------------------------------------------------
  // Eventos de los botones de pago
  // --------------------------------------------------

  function attachHandlers() {
    const buttons = Array.from(
      document.querySelectorAll('#pi-pay-btn')
    );

    if (!buttons.length) {
      console.warn(
        '[pi] No encontré #pi-pay-btn'
      );

      return;
    }

    console.debug(
      '[pi] Botones de pago listos:',
      buttons.length
    );

    buttons.forEach((btnEl) => {
      if (btnEl.__piBound) {
        return;
      }

      btnEl.__piBound = true;

      btnEl.addEventListener(
        'click',
        async () => {
          console.debug(
            '[pi] CLICK en botón'
          );

          if (!(await ensurePiReady())) {
            alert(
              'Abre esta página dentro de Pi Browser para pagar con Pi.'
            );

            return;
          }

          // 1. Solicitar permiso de pagos.
          const ok = await ensurePaymentsScope();

          console.debug(
            '[pi] scope payments =>',
            ok
          );

          if (!ok) {
            alert(
              'Debes autorizar el permiso de pagos de Pi para continuar.'
            );

            return;
          }

          // 2. Crear pedido en Django.
          try {
            const checkoutUrl =
              btnEl.getAttribute(
                'data-checkout-url'
              );

            console.debug(
              '[pi] startCheckout =>',
              checkoutUrl
            );

            const data = await startCheckout(
              checkoutUrl
            );

            console.debug(
              '[pi] checkout data =>',
              data
            );

            if (!data) {
              return;
            }

            // 3. Iniciar el pago en Pi.
            await createPayment(
              data.payment
            );
          } catch (error) {
            console.error(
              '[pi] error en click handler',
              error
            );

            alert(
              error.message ||
              'No se pudo iniciar el pago.'
            );
          }
        }
      );
    });
  }

  // --------------------------------------------------
  // Registrar eventos cuando el DOM esté preparado
  // --------------------------------------------------

  if (document.readyState === 'loading') {
    document.addEventListener(
      'DOMContentLoaded',
      attachHandlers
    );
  } else {
    attachHandlers();
  }

  // --------------------------------------------------
  // API pública opcional
  // --------------------------------------------------

  window.payWithPi = async (checkoutUrl) => {
    if (!(await ensurePiReady())) {
      alert(
        'Abre esta página dentro de Pi Browser para pagar con Pi.'
      );

      return;
    }

    const ok = await ensurePaymentsScope();

    if (!ok) {
      alert(
        'Debes autorizar el permiso de pagos de Pi para continuar.'
      );

      return;
    }

    const data = await startCheckout(
      checkoutUrl
    );

    if (data) {
      await createPayment(
        data.payment
      );
    }
  };
})();
