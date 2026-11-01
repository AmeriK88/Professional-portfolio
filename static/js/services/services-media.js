(() => {
  document.querySelectorAll(".service-media-content").forEach((media) => {
    const fallback = media.parentElement.querySelector("[data-service-fallback]");
    if (!fallback) return;

    const showFallback = () => {
      media.hidden = true;
      fallback.hidden = false;
    };

    media.addEventListener("error", showFallback, { once: true });

    if (media instanceof HTMLImageElement && media.complete && media.naturalWidth === 0) {
      showFallback();
    } else if (media instanceof HTMLVideoElement && media.error) {
      showFallback();
    }
  });
})();
