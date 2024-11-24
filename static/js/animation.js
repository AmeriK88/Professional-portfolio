document.addEventListener("DOMContentLoaded", function () {
    const text = "¡Hola! ¿Desarrollamos el futuro?";
    const typingElement = document.getElementById("typing-effect");
    let i = 0;

    function type() {
        if (i < text.length) {
            typingElement.textContent += text.charAt(i);
            i++;
            setTimeout(type, 100); // Ajusta el tiempo para cambiar la velocidad
        } else {
            typingElement.classList.add("cursor-blink"); // Activa la animación de parpadeo del cursor al finalizar
        }
    }

    type();
});
