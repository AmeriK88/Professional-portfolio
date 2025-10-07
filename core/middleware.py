from django.conf import settings
import re

class PiSandboxHeadersMiddleware:
    """
    Relaja cabeceras para funcionar embebido en Pi Browser (iframe) durante DEV/SANDBOX:
      - Quita X-Frame-Options
      - Normaliza CSP para permitir ancestros (frame-ancestors) de Pi
      - Elimina COOP/COEP/CORP que bloquean iframes cross-origin
    """

    FRAME_ANCESTORS = (
        # ‘self’ + dominios conocidos de Pi. Añade más si tu caso lo requiere.
        "frame-ancestors 'self' https://sandbox.minepi.com https://app.minepi.com "
        "https://*.minepi.com https://*.pi.delivery"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resp = self.get_response(request)

        # Solo en DEV/SANDBOX (evita relajar cabeceras en prod real)
        if getattr(settings, "PI_SANDBOX", False) or getattr(settings, "DEBUG", False):
            # 1) Quitar X-Frame-Options (ALLOWALL no es estándar; mejor eliminarla)
            if resp.has_header("X-Frame-Options"):
                try:
                    del resp["X-Frame-Options"]
                except KeyError:
                    pass

            # 2) Normalizar CSP: elimina frame-ancestors anteriores y añade los nuestros
            old_csp = resp.get("Content-Security-Policy", "")
            if old_csp:
                rest = re.sub(r"(^|;)\s*frame-ancestors[^;]*", "", old_csp, flags=re.I).strip().strip(";")
                new_csp = f"{rest}; {self.FRAME_ANCESTORS}" if rest else self.FRAME_ANCESTORS
            else:
                new_csp = self.FRAME_ANCESTORS
            resp["Content-Security-Policy"] = new_csp

            # 3) Quitar cabeceras que rompen iframes cross-origin
            for h in ("Cross-Origin-Opener-Policy", "Cross-Origin-Embedder-Policy", "Cross-Origin-Resource-Policy"):
                if resp.has_header(h):
                    try:
                        del resp[h]
                    except KeyError:
                        pass

            # 4) Habilitar pagos (útil para SDK Pi; ajusta si no lo necesitas)
            resp["Permissions-Policy"] = 'payment=(self "https://*.minepi.com")'

            # 5) Marca de diagnóstico
            resp["X-Pi-Sandbox-MW"] = "on"

        return resp
