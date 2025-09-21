(function () {
  const form = document.getElementById("register-form");
  if (!form) return;

  function getSiteKeyFromScriptTag() {
    const el = document.querySelector('script[src*="google.com/recaptcha/api.js?render="]');
    if (!el) return null;
    const idx = el.src.indexOf("render=");
    return idx > -1 ? el.src.slice(idx + 7) : null;
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const siteKey = getSiteKeyFromScriptTag();
    if (!siteKey || typeof grecaptcha === "undefined") {
      console.error("reCAPTCHA no está cargado o falta la site key.");
      alert("No se pudo cargar reCAPTCHA. Inténtalo de nuevo.");
      return;
    }

    try {
      const token = await grecaptcha.execute(siteKey, { action: "register" });
      const hidden = form.querySelector('input[name="recaptcha_token"]');
      if (hidden) hidden.value = token;
      form.submit();
    } catch (err) {
      console.error("reCAPTCHA error:", err);
      alert("No se pudo verificar reCAPTCHA. Inténtalo de nuevo.");
    }
  });
})();
