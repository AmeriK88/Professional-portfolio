from django.conf import settings

def pi_pricing(request):
    return {"PI_EUR_PER_PI": getattr(settings, "PI_EUR_PER_PI", None)}
