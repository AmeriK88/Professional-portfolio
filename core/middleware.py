
from django.conf import settings


class PiSandboxHeadersMiddleware:
    """
    Controla qu├® p├íginas pueden mostrarse dentro
    del iframe de Pi Network.

    Las rutas no autorizadas permanecen protegidas.
    """

    FRAME_ANCESTORS = (
        "frame-ancestors 'self' "
        "https://sandbox.minepi.com "
        "https://app.minepi.com "
        "https://*.minepi.com "
        "https://*.pi.delivery"
    )

    # Secciones p├║blicas permitidas.
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
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

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
            # Permitir iframe ├║nicamente desde los
            # or├¡genes indicados en FRAME_ANCESTORS.
            if response.has_header("X-Frame-Options"):
                del response["X-Frame-Options"]

            directives.append(self.FRAME_ANCESTORS)

        else:
            # Protecci├│n predeterminada.
            response["X-Frame-Options"] = "DENY"
            directives.append("frame-ancestors 'none'")

        response["Content-Security-Policy"] = (
            "; ".join(directives)
        )

        return response
