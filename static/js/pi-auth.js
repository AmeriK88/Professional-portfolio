// --- Utilidades ---
function getCsrf(name = "csrftoken") {
  return document.cookie.split("; ")
    .find(r => r.startsWith(name + "="))?.split("=")[1];
}

// Inicializa el SDK de Pi (llámalo lo antes posible)
export function initPiSdk({ sandbox = true } = {}) {
  if (!window.Pi) {
    console.error("Pi SDK no cargado (window.Pi undefined)");
    return;
  }
  // v2 es la versión actual del SDK moderno
  window.Pi.init({ version: "2.0", sandbox });
  // Debug info
  console.log("Pi SDK init:", { sandbox });
}

// Login con Pi y POST al backend de Django
export async function loginWithPi({ postUrl, onSuccessRedirect }) {
  try {
    if (!window.Pi) throw new Error("Pi SDK no inicializado");

    const { accessToken } = await window.Pi.authenticate(["username", "payments"]);

    const resp = await fetch(postUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
      body: JSON.stringify({ accessToken }),
    });

    if (!resp.ok) {
      const t = await resp.text().catch(() => "");
      throw new Error(`pi_login falló: ${resp.status} ${t}`);
    }

    // Redirección (prioriza ?next=)
    const urlNext = new URLSearchParams(window.location.search).get("next");
    window.location = urlNext || onSuccessRedirect || "/";
  } catch (e) {
    console.error(e);
    alert(
      "No se pudo iniciar sesión con Pi.\n" +
      "Verifica:\n• Estás en Pi Browser\n• Pi.init() ejecutado\n• Sandbox autorizado hoy"
    );
  }
}
