(function () {
  'use strict';

  const cfg = window.PI_CFG || {};
  console.debug('[pi] pi_payments.js cargado');

  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  function ensurePiReady() {
    if (!window.Pi) {
      console.warn('[pi] SDK Pi no disponible en window');
      return false;
    }
    try {
      Pi.init({ version: '2.0', sandbox: !!cfg.sandbox });
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

  function createPayment(paymentPayload) {
    const { approveUrl, completeUrl, cancelUrl, successUrl } = cfg;
    if (!approveUrl || !completeUrl || !cancelUrl) {
      throw new Error('Faltan URLs de callbacks de Pi en PI_CFG.');
    }

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
          } else {
            alert('No se pudo completar el pago en el servidor.');
          }
        } catch (e) {
          console.error(e);
          alert('Error completando el pago.');
        }
      },
      onCancel: async (paymentId) => {
        console.debug('[pi] onCancel', paymentId);
        try { await postJSON(cancelUrl, { paymentId }); } catch {}
      },
      onError: (error, payment) => {
        console.error('[pi] onError', error, payment);
        alert('Ha ocurrido un error con Pi. Reintenta en unos segundos.');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('pi-pay-btn');
    if (!btn) {
      console.warn('[pi] No encontré #pi-pay-btn');
      return;
    }
    console.debug('[pi] Botón de pago listo');

    btn.addEventListener('click', async () => {
      if (!ensurePiReady()) {
        alert('Abre esta página dentro de Pi Browser para pagar con Pi.');
        return;
      }
      try {
        const checkoutUrl = btn.getAttribute('data-checkout-url');
        const data = await startCheckout(checkoutUrl);
        if (!data) return; // probablemente redirigido a login
        createPayment(data.payment);
      } catch (e) {
        console.error(e);
        alert(e.message || 'No se pudo iniciar el pago.');
      }
    });
  });

  // API opcional
  window.payWithPi = async (checkoutUrl) => {
    if (!ensurePiReady()) return;
    const data = await startCheckout(checkoutUrl);
    if (data) createPayment(data.payment);
  };
})();
