from django.conf import settings

def recaptcha_keys(request):
    return {
        "RECAPTCHA_SITE_KEY": getattr(settings, "RECAPTCHA_SITE_KEY", ""),
    }
