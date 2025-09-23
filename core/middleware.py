class PiSandboxHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resp = self.get_response(request)

        # Permitir embed desde Pi Sandbox
        resp["X-Frame-Options"] = "ALLOWALL"
        resp["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://sandbox.minepi.com https://app.minepi.com"
        )

        # Limpia COEP/COOP que puedan estar bloqueando
        resp.pop("Cross-Origin-Opener-Policy", None)
        resp.pop("Cross-Origin-Embedder-Policy", None)
        resp.pop("Cross-Origin-Resource-Policy", None)

        return resp
