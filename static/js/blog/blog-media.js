(() => {
  const excerptLength = 180;

  document.querySelectorAll("[data-blog-excerpt-source]").forEach((excerpt) => {
    const source = excerpt.dataset.blogExcerptSource;
    const text = source
      .replace(/<(style|script|button|nav)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, " ")
      .replace(/<!--[\s\S]*?-->/g, " ")
      .replace(/<\/(?:p|div|li|h[1-6]|section|article|blockquote)\s*>/gi, " ")
      .replace(/<[^>]*>/g, " ");
    const textDecoder = document.createElement("textarea");
    textDecoder.innerHTML = text;
    let excerptText = textDecoder.value.replace(/\s+/g, " ").trim();

    if (excerptText.length > excerptLength) {
      excerptText = excerptText.slice(0, excerptLength - 1);
      const lastSpace = excerptText.lastIndexOf(" ");
      if (lastSpace > 0) excerptText = excerptText.slice(0, lastSpace);
      excerptText = `${excerptText.trimEnd()}…`;
    }

    excerpt.textContent = excerptText;
  });

  document.querySelectorAll("img[data-blog-media]").forEach((image) => {
    const fallback = image.parentElement.querySelector("[data-blog-fallback]");
    if (!fallback) return;

    const showFallback = () => {
      image.hidden = true;
      fallback.hidden = false;
    };

    image.addEventListener("error", showFallback, { once: true });

    if (image.complete && image.naturalWidth === 0) {
      showFallback();
    }
  });
})();
