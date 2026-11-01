(function () {
  const revealFallback = (frame) => {
    if (!frame) return;
    frame.classList.add('is-fallback');
    const fallback = frame.querySelector('.home-media-fallback');
    if (fallback) fallback.hidden = false;
  };

  document.addEventListener('error', (event) => {
    const media = event.target;
    if (media instanceof HTMLImageElement && media.matches('.home-media-image')) {
      const frame = media.closest('.home-media');
      media.hidden = true;
      media.removeAttribute('src');
      revealFallback(frame);
      return;
    }

    if (media instanceof HTMLVideoElement && media.matches('.home-preview-video')) {
      const frame = media.closest('.home-media');
      media.removeAttribute('src');
      media.removeAttribute('data-src');
      media.load();
      revealFallback(frame);
    }
  }, true);

  document.addEventListener('play', (event) => {
    const video = event.target;
    if (!(video instanceof HTMLVideoElement) || !video.matches('.home-preview-video')) return;

    const frame = video.closest('.home-media');
    if (!frame) return;
    frame.classList.remove('is-fallback');
    const fallback = frame.querySelector('.home-media-fallback');
    if (fallback) fallback.hidden = true;
  }, true);
})();
