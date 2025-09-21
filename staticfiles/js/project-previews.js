(function () {
  // Lazy-load de vídeos en tarjetas + control de reproducción
  const videos = Array.from(document.querySelectorAll('video.js-lazy-video[data-src]'));
  if (!('IntersectionObserver' in window) || videos.length === 0) return;

  let currentlyPlaying = null;

  const onEnterViewport = (video) => {
    if (!video.src) {
      video.src = video.dataset.src;       // carga el src al entrar en viewport
      // mantenemos preload="none"; el buffer empieza sólo si el usuario interactúa
    }
  };

  const onExitViewport = (video) => {
    // al salir, pausamos (y dejamos el src para conservar el poster/estado)
    if (!video.paused) video.pause();
    if (currentlyPlaying === video) currentlyPlaying = null;
  };

  // Pausa cualquier otro vídeo cuando uno empieza a reproducirse
  const pauseOthers = (self) => {
    videos.forEach(v => {
      if (v !== self && !v.paused) v.pause();
    });
    currentlyPlaying = self;
  };

  // Interacciones: reproducir en hover (desktop) o tap (móvil)
  const bindInteractions = (video) => {
    // Hover (desktop)
    video.addEventListener('mouseenter', () => {
      video.play().catch(() => {/* ignore: algunos navegadores requieren gesto */});
    });
    video.addEventListener('mouseleave', () => {
      if (!video.paused) video.pause();
    });

    // Tap / click (móvil o desktop)
    video.addEventListener('click', () => {
      if (video.paused) {
        video.play().catch(() => {/* ignore */});
      } else {
        video.pause();
      }
    });

    video.addEventListener('play', () => pauseOthers(video));
    // Por si la pestaña pierde foco, pausamos todo
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState !== 'visible' && !video.paused) video.pause();
    }, { passive: true });
  };

  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const video = entry.target;
      if (entry.isIntersecting) {
        onEnterViewport(video);
      } else {
        onExitViewport(video);
      }
    });
  }, {
    root: null,
    rootMargin: '200px',   // empieza a preparar cuando está cerca
    threshold: 0.01
  });

  videos.forEach(v => {
    bindInteractions(v);
    io.observe(v);
  });
})();
