
from django.conf import settings


class PiSandboxHeadersMiddleware:
    """
    Configura las cabeceras necesarias para permitir que la aplicación
    pueda incrustarse desde los orígenes autorizados de Pi Browser.

    Se activa exclusivamente mediante PI_BROWSER_EMBED_ENABLED=True.

    - Elimina X-Frame-Options cuando está habilitado.
    - Configura CSP frame-ancestors para limitar los orígenes permitidos.
    - Conserva las demás directivas CSP.
    - No modifica COOP, COEP ni CORP.
    - No depende de DEBUG ni de PI_SANDBOX.
    """

    FRAME_ANCESTORS = (
        "frame-ancestors 'self' "
        "https://sandbox.minepi.com "
        "https://app.minepi.com "
        "https://*.minepi.com "
        "https://*.pi.delivery"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(settings, "PI_BROWSER_EMBED_ENABLED", False):
            return response

        # Eliminar X-Frame-Options: CSP frame-ancestors controla
        # qué sitios pueden incrustar nuestra aplicación.
        if response.has_header("X-Frame-Options"):
            del response["X-Frame-Options"]

        # Recuperar la política CSP existente.
        existing_csp = response.get("Content-Security-Policy", "")

        # Conservar todas las directivas salvo frame-ancestors.
        directives = [
            directive.strip()
            for directive in existing_csp.split(";")
            if directive.strip()
            and directive.strip().split()[0].lower() != "frame-ancestors"
        ]

        # Añadir la política de incrustación autorizada.
        directives.append(self.FRAME_ANCESTORS)

        response["Content-Security-Policy"] = "; ".join(directives)

        return response
