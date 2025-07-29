document.addEventListener('DOMContentLoaded', () => {
  const animate = el => {
    const target = +el.dataset.target || 0;
    let value = 0;
    const step = Math.max(1, target / 40);

    const tick = () => {
      value = Math.min(target, value + step);
      el.innerText = Math.ceil(value);
      if (value < target) requestAnimationFrame(tick);
    };
    tick();
  };

  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        console.log('🌟 Contador visible:', entry.target);  // <- quita después
        animate(entry.target);
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.counter').forEach(el => io.observe(el));
});
