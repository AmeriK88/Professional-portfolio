
from django.conf import settings


def pi_settings(request):
    """
    Expone la configuración pública del SDK de Pi Network
    a las plantillas Django.
    """
    return {
        "PI_SANDBOX": settings.PI_SANDBOX,
    }
