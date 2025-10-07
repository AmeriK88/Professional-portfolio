from django.apps import AppConfig

class InboxConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inbox"

    def ready(self):
        # Importa señales al iniciar la app
        from . import signals  # noqa: F401
