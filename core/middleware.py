
from django.conf import settings


class PiSandboxHeadersMiddleware:
    """
<<<<<<< HEAD
    Configura las cabeceras necesarias para permitir que la aplicación
    pueda incrustarse desde los orígenes autorizados de Pi Browser.

    Se activa exclusivamente mediante PI_BROWSER_EMBED_ENABLED=True.

    - Elimina X-Frame-Options cuando está habilitado.
    - Configura CSP frame-ancestors para limitar los orígenes permitidos.
    - Conserva las demás directivas CSP.
    - No modifica COOP, COEP ni CORP.
    - No depende de DEBUG ni de PI_SANDBOX.
=======
    Controla qué páginas pueden mostrarse dentro
    del iframe de Pi Network.

    Las rutas no autorizadas permanecen protegidas.
>>>>>>> 3b90b37 (feat(pi): implement Pi Network authentication and payment integration)
    """

    FRAME_ANCESTORS = (
        "frame-ancestors 'self' "
        "https://sandbox.minepi.com "
        "https://app.minepi.com "
        "https://*.minepi.com "
        "https://*.pi.delivery"
<<<<<<< HEAD
=======
    )

    # Secciones públicas permitidas.
    PUBLIC_PREFIXES = (
        "/blog/",
        "/projects/",
        "/services/",
    )

    PUBLIC_PATHS = (
        "/",
        "/users/login/",
    )

    # Secciones privadas permitidas dentro de Pi.
    PRIVATE_PREFIXES = (
        "/orders/",
        "/inbox/",
        "/users/profile/",
>>>>>>> 3b90b37 (feat(pi): implement Pi Network authentication and payment integration)
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

<<<<<<< HEAD
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
=======
        if not getattr(
            settings,
            "PI_BROWSER_EMBED_ENABLED",
            False
        ):
            return response

        path = request.path_info

        is_public = (
            path in self.PUBLIC_PATHS
            or any(
                path.startswith(prefix)
                for prefix in self.PUBLIC_PREFIXES
            )
        )

        is_private_allowed = any(
            path.startswith(prefix)
            for prefix in self.PRIVATE_PREFIXES
        )

        allow_embedding = is_public or is_private_allowed

        existing_csp = response.get(
            "Content-Security-Policy",
            ""
        )

        directives = [
            directive.strip()
            for directive in existing_csp.split(";")
            if directive.strip()
            and directive.strip().split()[0].lower()
            != "frame-ancestors"
        ]

        if allow_embedding:
            # Permitir iframe únicamente desde los
            # orígenes indicados en FRAME_ANCESTORS.
            if response.has_header("X-Frame-Options"):
                del response["X-Frame-Options"]

            directives.append(self.FRAME_ANCESTORS)

        else:
            # Protección predeterminada.
            response["X-Frame-Options"] = "DENY"
            directives.append("frame-ancestors 'none'")

        response["Content-Security-Policy"] = (
            "; ".join(directives)
        )
>>>>>>> 3b90b37 (feat(pi): implement Pi Network authentication and payment integration)

        return response
