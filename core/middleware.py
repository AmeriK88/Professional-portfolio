from django.conf import settings
import re

class PiSandboxHeadersMiddleware:
    """
    Fuerza headers compatibles con Pi Browser / sandbox:
    - Elimina X-Frame-Options
    - Inserta/normaliza Content-Security-Policy con frame-ancestors permitiendo *.minepi.com
    - Elimina COOP/COEP/CORP que rompen iframes cross-origin
    Se ejecuta para cualquier respuesta (200/3xx/4xx/5xx, estáticos de WhiteNoise incluidos).
    """
    # Incluimos wildcard por si Pi cambia subdominios internos.
    FRAME_ANCESTORS = (
        "frame-ancestors 'self' https://sandbox.minepi.com https://app.minepi.com https://*.minepi.com"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resp = self.get_response(request)

        # Actívalo siempre que estés en prod o en sandbox/dev según var de entorno.
        if getattr(settings, "PI_SANDBOX", False) or getattr(settings, "DEBUG", False) or True:
            # 1) Quitar X-Frame-Options
            if resp.has_header("X-Frame-Options"):
                try:
                    del resp["X-Frame-Options"]
                except KeyError:
                    pass

            # 2) Normalizar CSP (quitamos cualquier frame-ancestors previo y ponemos el nuestro)
            old_csp = resp.get("Content-Security-Policy", "")
            if old_csp:
                # Eliminar cualquier frame-ancestors existente
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

            # 4) Marca de diagnóstico
            resp["X-Pi-Sandbox-MW"] = "on"

        return resp
