// static/js/counter.js
(() => {
  const els = document.querySelectorAll(".counter");
  if (!els.length) return;

  const fmt = new Intl.NumberFormat(undefined); // separadores de miles

  const animate = (el) => {
    const target = parseInt(el.dataset.target || "0", 10);
    const duration = parseInt(el.dataset.duration || "900", 10); // ms (opcional)
    const from = parseInt(el.dataset.from || "0", 10);

    const start = performance.now();

    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      const value = Math.round(from + (target - from) * eased);
      el.textContent = fmt.format(value);
      if (t < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  };

  const io = "IntersectionObserver" in window
    ? new IntersectionObserver((entries, obs) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            animate(e.target);
            obs.unobserve(e.target);
          }
        }
      }, { threshold: 0.4 })
    : null;

  els.forEach((el) => {
    if (io) io.observe(el);
    else animate(el); // fallback sin IO
  });
})();
