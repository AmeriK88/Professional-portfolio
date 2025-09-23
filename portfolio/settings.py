from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from pathlib import Path
import environ
import dj_database_url
import os

# Usar PyMySQL como drop-in de mysqlclient si está disponible
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

# --- Paths base ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Entorno (.env) ---
env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# --- Seguridad / entorno ---
# Fallback: si no hay SECRET_KEY, intenta con DEAFAULT_SK (como lo tienes escrito en tus variables),
# y si tampoco existe, usa "change-me".
SECRET_KEY = env("SECRET_KEY", default=env("DEAFAULT_SK", default="DEAFAULT_SK"))
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Pi Payments
PI_API_KEY = env("PI_API_KEY", default="")

# Detrás de proxy (Railway / proxies)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# --- Apps ---
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "blog",
    "core",
    "projects",
    "services.apps.ServicesConfig",
    "pi_payments",
    "users.apps.UsersConfig",
    "orders",
    "axes",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- Pi Sandbox (solo para DEV/SANDBOX) ---
PI_SANDBOX = env.bool("PI_SANDBOX", default=True)  

# settings.py
if PI_SANDBOX or DEBUG:
    MIDDLEWARE = [m for m in MIDDLEWARE if m != "django.middleware.clickjacking.XFrameOptionsMiddleware"]




ROOT_URLCONF = "portfolio.urls"

# settings.py
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,  # busca plantillas dentro de cada app
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Opcional: expone STATIC_URL en plantillas
                "django.template.context_processors.static",
                # >>> Tu context processor para la site key <<<
                "users.context_processors.recaptcha_keys",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend", 
    "django.contrib.auth.backends.ModelBackend",
]


WSGI_APPLICATION = "portfolio.wsgi.application"

# Endurece cookies/HSTS en no-DEBUG
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Base de datos ---
DB_URL = env("DATABASE_URL", default=None)

def _is_mysql_url(url: str | None) -> bool:
    """Detecta si la URL apunta a MySQL (mysql:// o mysql+pymysql://)."""
    return bool(url) and (url.startswith("mysql://") or url.startswith("mysql+pymysql://"))

if DB_URL:
    # Sólo forzar SSL en no-MySQL. MySQL no acepta 'sslmode'.
    db_default = dj_database_url.config(
        default=DB_URL,
        conn_max_age=600,
        ssl_require=(not DEBUG and not _is_mysql_url(DB_URL)),
    )

    # Limpiar 'sslmode' si existiera (evita error con MySQL)
    opts = dict(db_default.get("OPTIONS", {}))
    opts.pop("sslmode", None)

    # Asegura charset en MySQL si no viene en la URL
    if _is_mysql_url(DB_URL):
        opts.setdefault("charset", "utf8mb4")

    db_default["OPTIONS"] = opts
    DATABASES = {"default": db_default}
else:
    # Fallback por variables sueltas
    DATABASES = {
        "default": {
            "ENGINE": env("DB_ENGINE"),
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST"),
            "PORT": env("DB_PORT"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",
            },
        }
    }

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Email backend (consola para desarrollo)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- UNFOLD CONFIG ---
UNFOLD = {
    "SITE_TITLE": "Portfolio Admin",
    "SITE_HEADER": "José Admin",
    "SITE_SUBHEADER": "Developer Dashboard",
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": lambda request: static("img/admin/icon-dark.svg"),
        "dark": lambda request: static("img/admin/icon-light.svg"),
    },
    "SITE_LOGO": {
        "light": lambda request: static("img/admin/logo-light.png"),
        "dark": lambda request: static("img/admin/jf_logo.png"),
    },
    "SITE_SYMBOL": "code",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("img/admin/icon-light.svg"),
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": False,
    # "THEME": "dark",  # o "light" si quisieras forzar
    "LOGIN": {
        "image": lambda request: static("img/admin/login-bg.svg"),
        "redirect_after": lambda request: reverse_lazy("admin:projects_project_changelist"),
    },
    "COLORS": {
        "primary": {
            "50": "250, 245, 255",
            "100": "243, 232, 255",
            "200": "233, 213, 255",
            "300": "216, 180, 254",
            "400": "192, 132, 252",
            "500": "168, 85, 247",
            "600": "147, 51, 234",
            "700": "126, 34, 206",
            "800": "107, 33, 168",
            "900": "88, 28, 135",
            "950": "59, 7, 100",
        }
    },
    "SIDEBAR": {
        "show_search": True,
        "command_search": False,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Posts"),
                        "icon": "article",
                        "link": reverse_lazy("admin:blog_post_changelist"),
                    },
                    {
                        "title": _("Projects"),
                        "icon": "work",
                        "link": reverse_lazy("admin:projects_project_changelist"),
                    },
                    {
                        "title": _("Services"),
                        "icon": "sell",
                        "link": reverse_lazy("admin:services_service_changelist"),
                    },
                ],
            },
        ],
    },
    "DASHBOARD_CALLBACK": "portfolio.admin_dashboard.dashboard_callback",
}


# --- Logging ---
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True) 

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # conserva loggers de Django/terceros
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s %(clientip)s %(message)s",
        },
        "simple": {"format": "%(levelname)s: %(message)s"},
    },
    "filters": {
        # añade IP del cliente si está en request (no siempre disponible)
        "client_ip": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: setattr(
                record, "clientip", getattr(record, "clientip", "")
            ) or True,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO" if DEBUG else "WARNING",
            "formatter": "simple",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "filename": str(LOG_DIR / "security.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
            "filters": ["client_ip"],
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
        },
    },
    "loggers": {
        # Bloqueos e intentos que registra django-axes
        "axes": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # Alertas de seguridad de Django (CSRF, SuspiciousOperation, etc.)
        "django.security": {
            "handlers": ["security_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Errores de petición (500, tracebacks)
        "django.request": {
            "handlers": ["security_file", "console"] + ([] if DEBUG else ["mail_admins"]),
            "level": "ERROR",
            "propagate": False,
        },
        # Autenticación (logins/logout fallidos, cambios de password)
        "django.contrib.auth": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # (Opcional) tu app users para registrar eventos propios
        "users": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# --- Seguridad extra ---
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# --- Usuario custom ---
AUTH_USER_MODEL = "users.User"

# --- i18n / zona horaria ---
LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_TZ = True
USE_I18N = True
USE_L10N = True

# --- Login redirects ---
# --- Archivos estáticos / media ---
USE_VOLUME_MEDIA = env.bool("USE_VOLUME_MEDIA", default=False)

MEDIA_URL = "/media/"
if USE_VOLUME_MEDIA:
    # Producción en Railway (volumen montado en /data)
    MEDIA_ROOT = "/data/media"
else:
    # Local
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")

os.makedirs(MEDIA_ROOT, exist_ok=True)

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365 

LOGIN_URL = reverse_lazy("users:login")
LOGIN_REDIRECT_URL = reverse_lazy("users:profile")   
LOGOUT_REDIRECT_URL = "/" 


# Marcar como "immutable" los ficheros con hash en el nombre (los de Manifest)
def whitenoise_immutable_test(path, url):
    import re
    filename = path.rsplit("/", 1)[-1]
    return bool(re.search(r"\.[0-9a-f]{8,}\.", filename))

WHITENOISE_IMMUTABLE_FILE_TEST = whitenoise_immutable_test

# Añadir stale-while-revalidate para aún más suavidad en recargas
def whitenoise_add_headers(headers, path, url):
    # WhiteNoise ya pondrá max-age; aquí completamos con SWR si es immutable
    if WHITENOISE_IMMUTABLE_FILE_TEST(path, url):
        headers["Cache-Control"] = "public, max-age=31536000, immutable, stale-while-revalidate=86400"

WHITENOISE_ADD_HEADERS_FUNCTION = whitenoise_add_headers

# Opcional:
# WHITENOISE_KEEP_ONLY_HASHED_FILES = True

# --- reCAPTCHA v3 ---
RECAPTCHA_SITE_KEY = env("RECAPTCHA_SITE_KEY", default="")
RECAPTCHA_SECRET_KEY = env("RECAPTCHA_SECRET_KEY", default="")
RECAPTCHA_MIN_SCORE = env.float("RECAPTCHA_MIN_SCORE", default=0.5)


# Configuración básica
AXES_FAILURE_LIMIT = 5  # máximo de intentos
AXES_COOLOFF_TIME = 1  # horas bloqueado
AXES_LOCKOUT_TEMPLATE = 'errors/locked_out.html'

# si usas django-csp
CSP_FRAME_ANCESTORS = ("'self'", "https://sandbox.minepi.com", "https://app.minepi.com")


# --- Default PK field ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
