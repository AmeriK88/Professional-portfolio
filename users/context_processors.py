from django.conf import settings

def recaptcha_keys(request):
    return {
        "RECAPTCHA_SITE_KEY": getattr(settings, "RECAPTCHA_SITE_KEY", ""),
    }

def pi_flags(request):
    return {"PI_ONLY_LOGIN": getattr(settings, "PI_ONLY_LOGIN", False)}