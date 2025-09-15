/* pi_payments.js */
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
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify(body)
    });
  }

  function toAmount(value) {
    if (typeof value === 'number') return value;
    const s = String(value).trim().replace(',', '.');
    const n = Number(s);
    if (Number.isNaN(n)) {
      throw new Error('Importe inválido: ' + value);
    }
    return n;
  }

  async function doPay(title, amount, serviceId) {
    if (!ensurePiReady()) {
      alert('Abre esta página dentro de Pi Browser para pagar con Pi.');
      return;
    }

    let amt;
    try {
      amt = toAmount(amount);
    } catch (err) {
      console.error('[pi] Importe inválido:', err);
      alert('Importe inválido.');
      return;
    }

    const paymentData = {
      amount: amt,
      memo: `Pago servicio: ${title}`,
      metadata: { service_id: serviceId }
    };

    const callbacks = {
      onReadyForServerApproval: async (paymentId) => {
        console.debug('[pi] onReadyForServerApproval', paymentId);
        if (cfg.approveUrl) await postJSON(cfg.approveUrl, { paymentId });
      },
      onReadyForServerCompletion: async (paymentId, txid) => {
        console.debug('[pi] onReadyForServerCompletion', paymentId, txid);
        if (!cfg.completeUrl) return;
        const r = await postJSON(cfg.completeUrl, { paymentId, txid });
        if (r.ok) {
          const base = cfg.successUrl || '/';
          const sep = base.includes('?') ? '&' : '?';
          window.location.href = `${base}${sep}pid=${encodeURIComponent(paymentId)}`;
        } else {
          alert('No se pudo completar el pago. Intenta de nuevo.');
        }
      },
      onCancel: async (paymentId) => {
        console.debug('[pi] onCancel', paymentId);
        if (cfg.cancelUrl) await postJSON(cfg.cancelUrl, { paymentId });
      },
      onError: (error, payment) => {
        console.error('[pi] onError', error, payment);
        alert('Ha ocurrido un error con Pi. Reintenta en unos segundos.');
      }
    };

    try {
      await Pi.createPayment(paymentData, callbacks);
    } catch (e) {
      console.error('[pi] createPayment falló:', e);
      alert('No se pudo iniciar el flujo de pago.');
    }
  }

  // Vincular el botón al cargar el DOM
  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('pi-pay-btn');
    if (!btn) {
      console.warn('[pi] No encontré #pi-pay-btn');
      return;
    }
    console.debug('[pi] Botón de pago listo');

    btn.addEventListener('click', () => {
      const title = btn.getAttribute('data-title') || '';
      const amount = btn.getAttribute('data-amount') || '';
      const sid = Number(btn.getAttribute('data-service-id') || '0');
      doPay(title, amount, sid);
    });
  });

  // Por si quieres seguir usando el inline, lo exponemos también
  window.payWithPi = (title, amount, serviceId) => doPay(title, amount, serviceId);
})();
