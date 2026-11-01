document.addEventListener('DOMContentLoaded', () => {
  const typingElement = document.getElementById('typing-effect');
  if (!typingElement || typingElement.dataset.typingInitialized === 'true') return;

  const text = typingElement.textContent.trim();
  if (!text) return;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  typingElement.dataset.typingInitialized = 'true';
  typingElement.textContent = '';
  let i = 0;

  (function type() {
    if (i < text.length) {
      typingElement.textContent += text.charAt(i++);
      setTimeout(type, 100);
    } else {
      typingElement.classList.add('cursor-blink');
    }
  })();
});
