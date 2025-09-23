from django.conf import settings

class PiSandboxHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(settings, "PI_SANDBOX", False) or getattr(settings, "DEBUG", False):
            # 1) Eliminar X-Frame-Options por completo (NO poner ALLOWALL)
            if response.has_header("X-Frame-Options"):
                del response["X-Frame-Options"]

            # 2) Permitir ser embeído por Pi Browser con CSP moderna
            #    (si ya tienes CSP previa, idealmente añade/mergea frame-ancestors)
            response["Content-Security-Policy"] = (
                "frame-ancestors https://sandbox.minepi.com https://app.minepi.com"
            )

            # 3) Quitar COOP/COEP/CORP que rompen iframes cross-origin
            for h in (
                "Cross-Origin-Opener-Policy",
                "Cross-Origin-Embedder-Policy",
                "Cross-Origin-Resource-Policy",
            ):
                if response.has_header(h):
                    del response[h]

        return response
