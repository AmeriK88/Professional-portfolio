# core/middleware.py
from django.conf import settings
import re

class PiSandboxHeadersMiddleware:
    FRAME_ANCESTORS = "frame-ancestors https://sandbox.minepi.com https://app.minepi.com"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(settings, "PI_SANDBOX", False) or getattr(settings, "DEBUG", False):
            # 1) Quitar X-Frame-Options
            if response.has_header("X-Frame-Options"):
                del response["X-Frame-Options"]

            # 2) CSP: si ya había CSP, elimina frame-ancestors previo y añade el nuestro
            old_csp = response.get("Content-Security-Policy", "")
            if old_csp:
                rest = re.sub(r"(?:^|;)\s*frame-ancestors[^;]*", "", old_csp, flags=re.I).strip().strip(";")
                new_csp = f"{rest}; {self.FRAME_ANCESTORS}" if rest else self.FRAME_ANCESTORS
            else:
                new_csp = self.FRAME_ANCESTORS
            response["Content-Security-Policy"] = new_csp

            # 3) Quitar cabeceras que rompen iframes cross-origin
            for h in ("Cross-Origin-Opener-Policy", "Cross-Origin-Embedder-Policy", "Cross-Origin-Resource-Policy"):
                if response.has_header(h):
                    del response[h]

            # 4) Sello de depuración: verifica que pasó por aquí
            response["X-Pi-Sandbox-MW"] = "on"

        return response
