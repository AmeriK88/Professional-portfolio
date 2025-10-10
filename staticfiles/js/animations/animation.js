document.addEventListener('DOMContentLoaded', () => {
  const typingElement = document.getElementById('typing-effect');
  if (!typingElement) return;     

  const text = '¡Hola! ¿Desarrollamos el futuro?';
  let i = 0;

  (function type() { 
    if (i < text.length) {
      typingElement.textContent += text[i++];
      setTimeout(type, 100);
    } else {
      typingElement.classList.add('cursor-blink');
    }
  })();
});
