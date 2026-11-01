(() => {
  document.querySelectorAll(".projects-media").forEach((container) => {
    const media = container.querySelector(".projects-media-content");
    const fallback = container.querySelector(".projects-media-fallback");
    if (!media || !fallback) return;

    const showFallback = () => {
      media.hidden = true;
      fallback.hidden = false;
      const label = fallback.querySelector("span");
      if (label) label.textContent = "Vista previa no disponible";
    };

    media.addEventListener("error", showFallback, { once: true });

    if (media instanceof HTMLVideoElement) {
      media.addEventListener("play", () => {
        fallback.hidden = true;
      }, { once: true });
    }

    if (media instanceof HTMLImageElement && media.complete && media.naturalWidth === 0) {
      showFallback();
    }
  });
})();
