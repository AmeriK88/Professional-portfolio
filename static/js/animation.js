document.addEventListener('DOMContentLoaded', () => {
  const typingElement = document.getElementById('typing-effect');
  if (!typingElement) return;        // ← ① aborta si no existe

  const text = '¡Hola! ¿Desarrollamos el futuro?';
  let i = 0;

  (function type() {                 // ← ② IIFE
    if (i < text.length) {
      typingElement.textContent += text[i++];
      setTimeout(type, 100);
    } else {
      typingElement.classList.add('cursor-blink');
    }
  })();
});
