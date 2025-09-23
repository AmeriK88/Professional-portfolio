# core/middleware.py
from django.conf import settings

class PiSandboxHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(settings, "PI_SANDBOX", False) or getattr(settings, "DEBUG", False):
            # Permitir embed desde Pi
            response["X-Frame-Options"] = "ALLOWALL"

            # CSP: permitir que Pi Sandbox/App te enmarquen
            # (Si ya tenías CSP compleja, aquí la sobrescribimos para sandbox;
            # si prefieres, detecta y sustituye solo frame-ancestors).
            response["Content-Security-Policy"] = (
                "frame-ancestors 'self' https://sandbox.minepi.com https://app.minepi.com"
            )

            # Quitar headers que bloquean iframes si existen
            for h in (
                "Cross-Origin-Opener-Policy",
                "Cross-Origin-Embedder-Policy",
                "Cross-Origin-Resource-Policy",
            ):
                if response.has_header(h):
                    try:
                        del response[h]
                    except KeyError:
                        pass

        return response
