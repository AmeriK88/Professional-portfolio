from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.contrib import messages

@receiver(user_logged_in, dispatch_uid="users_greet_login_once")
def greet_login(sender, user, request, **kwargs):
    messages.success(request, "Has iniciado sesión. ¡Bienvenido de nuevo!")

@receiver(user_login_failed, dispatch_uid="users_warn_bad_login_once")
def warn_bad_login(sender, credentials, request, **kwargs):
    messages.error(request, "Credenciales inválidas. Revisa usuario o contraseña.")
