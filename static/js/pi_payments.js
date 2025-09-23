(function () {
  'use strict';

  // Evita doble init si el script se incluye dos veces
  if (window.__PI_PAY_INIT__) return;
  window.__PI_PAY_INIT__ = true;

  const cfg = window.PI_CFG || {};
  console.debug('[pi] pi_payments.js cargado');

  // ---- Helpers ----
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  // ---- Detección de entorno seguro / Pi ----
  function isSecurePublicContext() {
    const isHttps = location.protocol === 'https:';
    const isLocal = /^(localhost|127\.0\.0\.1)$/i.test(location.hostname);
    return isHttps && !isLocal;
  }

  function isPiEnv() {
    const ua = navigator.userAgent || '';
    const inPiUA = /PiBrowser/i.test(ua);

    // ¿Nos está enmarcando Pi (portal o app)?
    let inPiFrame = false;
    try {
      if (window !== window.top && document.referrer) {
        const ref = new URL(document.referrer);
        inPiFrame =
          ref.origin === 'https://sandbox.minepi.com' ||
          ref.origin === 'https://app.minepi.com';
      }
    } catch (_) {}
    return inPiUA || inPiFrame;
  }

  // ---- Inicialización del SDK (gateado) ----
  function ensurePiReady() {
    if (!window.Pi) {
      console.warn('[pi] SDK Pi no disponible en window');
      return false;
    }
    // Solo inicializamos si estamos en Pi y en un contexto HTTPS público
    if (!isPiEnv() || !isSecurePublicContext()) {
      console.warn('[pi] Fuera de entorno Pi o sin HTTPS público; no inicializo SDK', {
        piEnv: isPiEnv(),
        httpsPublic: isSecurePublicContext(),
        ua: navigator.userAgent,
        href: location.href,
        referrer: document.referrer
      });
      return false;
    }
    if (window.__PI_INIT_DONE__) return true;
    try {
      Pi.init({ version: '2.0', sandbox: !!cfg.sandbox });
      window.__PI_INIT_DONE__ = true;
      console.debug('[pi] Pi.init OK, sandbox =', !!cfg.sandbox);
      return true;
    } catch (e) {
      console.error('[pi] Pi.init falló:', e);
      return false;
    }
  }

  async function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || '',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(body || {})
    });
  }

  async function startCheckout(checkoutUrl) {
    if (!checkoutUrl) throw new Error('No se definió data-checkout-url en el botón.');
    const res = await fetch(checkoutUrl, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    // Si el backend te redirige a login, seguimos esa redirección
    if (res.redirected || (res.url && res.url.includes('/login'))) {
      window.location.href = res.url || ('/login/?next=' + window.location.pathname);
      return null;
    }

    if (!res.ok) throw new Error('No se pudo iniciar el pedido.');
    const data = await res.json();
    if (!data.ok || !data.payment) throw new Error('Respuesta de checkout inválida.');
    return data; // { ok, order_number, payment }
  }

  // ---- Scope payments ----
  let paymentsAuthPromise = null;

  async function ensurePaymentsScope() {
    if (!ensurePiReady()) return false;

    if (!paymentsAuthPromise) {
      const onIncompletePaymentFound = async (payment) => {
        try {
          console.debug('[pi] incomplete payment found', payment);
          const pid  = payment?.identifier || payment?.paymentId || payment?.id;
          const txid = payment?.transaction?.txid;

          if (pid && txid) {
            if (cfg.completeUrl) await postJSON(cfg.completeUrl, { paymentId: pid, txid });
          } else if (pid) {
            if (cfg.approveUrl) await postJSON(cfg.approveUrl, { paymentId: pid });
          }
        } catch (e) {
          console.error('[pi] onIncompletePaymentFound error', e);
        }
      };

      paymentsAuthPromise = window.Pi
        .authenticate(['payments'], onIncompletePaymentFound)
        .then(() => true)
        .catch(err => {
          console.error('[pi] authenticate error', err);
          paymentsAuthPromise = null;
          return false;
        });
    }

    return paymentsAuthPromise;
  }

  // ---- Crear pago ----
  async function createPayment(paymentPayload) {
    const { approveUrl, completeUrl, cancelUrl, successUrl } = cfg;
    if (!approveUrl || !completeUrl || !cancelUrl) {
      throw new Error('Faltan URLs de callbacks de Pi en PI_CFG.');
    }

    const authed = await ensurePaymentsScope();
    if (!authed) {
      throw new Error('Debes autorizar el permiso de pagos de Pi para continuar.');
    }

    return new Promise((resolve, reject) => {
      try {
        window.Pi.createPayment(paymentPayload, {
          onReadyForServerApproval: async (paymentId) => {
            console.debug('[pi] onReadyForServerApproval', paymentId);
            try {
              const r = await postJSON(approveUrl, { paymentId });
              if (!r.ok) throw new Error('Fallo aprobando en servidor');
            } catch (e) {
              console.error(e);
              alert('Error aprobando el pago. Intenta de nuevo.');
            }
          },
          onReadyForServerCompletion: async (paymentId, txid) => {
            console.debug('[pi] onReadyForServerCompletion', paymentId, txid);
            try {
              const r = await postJSON(completeUrl, { paymentId, txid });
              if (r.ok) {
                const base = successUrl || '/';
                const url = new URL(base, window.location.origin);
                url.searchParams.set('pid', paymentId);
                window.location.assign(url.toString());
                resolve({ paymentId, txid });
              } else {
                alert('No se pudo completar el pago en el servidor.');
                reject(new Error('complete failed'));
              }
            } catch (e) {
              console.error(e);
              alert('Error completando el pago.');
              reject(e);
            }
          },
          onCancel: async (paymentId) => {
            console.debug('[pi] onCancel', paymentId);
            try { await postJSON(cancelUrl, { paymentId }); } catch {}
            // No rechazamos: es cancelación de usuario
          },
          onError: (error, payment) => {
            console.error('[pi] onError', error, payment);
            alert('Ha ocurrido un error con Pi. Reintenta en unos segundos.');
            reject(error);
          }
        });
      } catch (err) {
        console.error('[pi] createPayment falló', err);
        if (String(err?.message || err).includes('payments')) {
          alert('No se pudo crear el pago porque falta el permiso de pagos. Autorízalo y reintenta.');
        } else {
          alert('No se pudo crear el pago. Intenta de nuevo.');
        }
        reject(err);
      }
    });
  }

  // ---- UI (múltiples botones, sin variables fuera de scope) ----
  function attachHandlers() {
    const buttons = Array.from(document.querySelectorAll('#pi-pay-btn'));
    if (!buttons.length) {
      console.warn('[pi] No encontré #pi-pay-btn');
      return;
    }

    console.debug('[pi] Botones de pago listos:', buttons.length);

    buttons.forEach((btnEl) => {
      if (btnEl.__piBound) return; // evita duplicar listeners
      btnEl.__piBound = true;

      btnEl.addEventListener('click', async () => {
        console.debug('[pi] CLICK en botón');
        if (!ensurePiReady()) {
          alert('Abre esta página dentro de Pi Browser para pagar con Pi.');
          return;
        }

        // 1) Scope payments
        const ok = await ensurePaymentsScope();
        console.debug('[pi] scope payments =>', ok);
        if (!ok) {
          alert('Debes autorizar el permiso de pagos de Pi para continuar.');
          return;
        }

        // 2) Checkout desde backend
        try {
          const checkoutUrl = btnEl.getAttribute('data-checkout-url');
          console.debug('[pi] startCheckout =>', checkoutUrl);
          const data = await startCheckout(checkoutUrl);
          console.debug('[pi] checkout data =>', data);
          if (!data) return; // redirigido a login
          // 3) Inicia pago
          await createPayment(data.payment);
        } catch (e) {
          console.error('[pi] error en click handler', e);
          alert(e.message || 'No se pudo iniciar el pago.');
        }
      });
    });
  }

  // Carga segura
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachHandlers);
  } else {
    attachHandlers();
  }

  // API opcional
  window.payWithPi = async (checkoutUrl) => {
    if (!ensurePiReady()) {
      alert('Abre esta página dentro de Pi Browser para pagar con Pi.');
      return;
    }
    const ok = await ensurePaymentsScope();
    if (!ok) {
      alert('Debes autorizar el permiso de pagos de Pi para continuar.');
      return;
    }
    const data = await startCheckout(checkoutUrl);
    if (data) await createPayment(data.payment);
  };
})();
