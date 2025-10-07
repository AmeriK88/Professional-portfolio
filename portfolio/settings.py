from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.staticfiles.storage import StaticFilesStorage as _DevStorage
from pathlib import Path
from decimal import Decimal
import environ
import dj_database_url
from urllib.parse import urlparse
import os
import re

# Use PyMySQL as a drop-in replacement for mysqlclient if available
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

# --- Base paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment (.env) ---
env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# --- External commands ---
FFMPEG_CMD = os.getenv("FFMPEG_CMD", "ffmpeg")

# --- Security / environment ---
# Fallback: if SECRET_KEY is missing, try DEAFAULT_SK (as spelled in your env),
# otherwise use a placeholder.
SECRET_KEY = env("SECRET_KEY", default=env("DEAFAULT_SK", default="DEAFAULT_SK"))
DEBUG = env.bool("DEBUG", default=False)

# NOTE: Put hostnames only in ALLOWED_HOSTS. Wildcards like ".devtunnels.ms" are allowed.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# NOTE: CSRF_TRUSTED_ORIGINS must include scheme and MUST NOT have a trailing slash
# e.g., "https://*.devtunnels.ms", "http://127.0.0.1:8000"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Pi Payments
PI_API_KEY = env("PI_API_KEY", default="")

# Behind proxy (Railway / dev tunnels)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Pi ↔ EUR conversion (EUR per π)
PI_EUR_PER_PI = Decimal(str(env("PI_EUR_PER_PI", default="0.30")))

# Optional: force Pi-only login flows in your app if you use it
PI_ONLY_LOGIN = env("PI_ONLY_LOGIN", default=False)

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
]

# --- Pi Sandbox (DEV/SANDBOX only) ---
PI_SANDBOX = env.bool("PI_SANDBOX", default=True)
if PI_SANDBOX or DEBUG:
    # Asegura que no esté XFrameOptionsMiddleware y añade el tuyo
    MIDDLEWARE = [m for m in MIDDLEWARE if m != "django.middleware.clickjacking.XFrameOptionsMiddleware"]
    MIDDLEWARE.append("core.middleware.PiSandboxHeadersMiddleware")

ROOT_URLCONF = "portfolio.urls"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Expose STATIC_URL in templates
                "django.template.context_processors.static",
                # reCAPTCHA keys in templates
                "users.context_processors.recaptcha_keys",
                # Pi pricing (EUR/π) in templates
                "pi_payments.context_processors.pi_pricing",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

WSGI_APPLICATION = "portfolio.wsgi.application"

# --- Database ---
DB_URL = env("DATABASE_URL", default=None)

def _is_mysql_url(url: str | None) -> bool:
    """Detect if URL points to MySQL (mysql:// or mysql+pymysql://)."""
    return bool(url) and (url.startswith("mysql://") or url.startswith("mysql+pymysql://"))

if DB_URL:
    # Only force SSL for non-MySQL URLs. MySQL does not accept "sslmode".
    db_default = dj_database_url.config(
        default=DB_URL,
        conn_max_age=600,
        ssl_require=(not DEBUG and not _is_mysql_url(DB_URL)),
    )
    opts = dict(db_default.get("OPTIONS", {}))
    opts.pop("sslmode", None)
    if _is_mysql_url(DB_URL):
        opts.setdefault("charset", "utf8mb4")
    db_default["OPTIONS"] = opts
    DATABASES = {"default": db_default}
else:
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
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Email backend (console in development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- UNFOLD ADMIN CONFIG ---
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
    # "THEME": "dark",
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
                    {"title": _("Dashboard"), "icon": "dashboard", "link": reverse_lazy("admin:index")},
                    {"title": _("Posts"), "icon": "article", "link": reverse_lazy("admin:blog_post_changelist")},
                    {"title": _("Projects"), "icon": "work", "link": reverse_lazy("admin:projects_project_changelist")},
                    {"title": _("Services"), "icon": "sell", "link": reverse_lazy("admin:services_service_changelist")},
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
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s %(clientip)s %(message)s"},
        "simple": {"format": "%(levelname)s: %(message)s"},
    },
    "filters": {
        "client_ip": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: setattr(record, "clientip", getattr(record, "clientip", "")) or True,
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "level": "INFO" if DEBUG else "WARNING", "formatter": "simple"},
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "filename": str(LOG_DIR / "security.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "verbose",
            "filters": ["client_ip"],
        },
        "mail_admins": {"class": "django.utils.log.AdminEmailHandler", "level": "ERROR"},
    },
    "loggers": {
        "axes": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["security_file", "console"], "level": "WARNING", "propagate": False},
        "django.request": {
            "handlers": ["security_file", "console"] + ([] if DEBUG else ["mail_admins"]),
            "level": "ERROR",
            "propagate": False,
        },
        "django.contrib.auth": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
        "users": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
    },
}

def _as_str_list(value) -> list[str]:
    """Normalize env values to a clean list[str]. Accepts list/tuple/str/bytes/None."""
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    if isinstance(value, (bytes, str)):
        s = value.decode() if isinstance(value, bytes) else value
        return [p.strip() for p in s.split(",") if p.strip()]
    return []

# Ensure well-typed lists for linters and runtime
ALLOWED_HOSTS = _as_str_list(ALLOWED_HOSTS)
CSRF_TRUSTED_ORIGINS = _as_str_list(CSRF_TRUSTED_ORIGINS)

# Build a host set for tunnel detection (include hostnames from CSRF origins)
_host_pool: set[str] = set(ALLOWED_HOSTS)
_host_pool.update(filter(None, (urlparse(u).hostname for u in CSRF_TRUSTED_ORIGINS)))

# --- Cookies / CSRF policy (single authoritative block) ---
#   - PROD (DEBUG=False): cookies secure + SameSite=None + HSTS
#   - DEV (DEBUG=True):
#       * 127.0.0.1: Lax no-seguro
#       * túnel HTTPS: Secure + SameSite=None
USING_TUNNEL = any(h and h.endswith((".devtunnels.ms", ".ngrok.io")) for h in _host_pool)

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"

    SECURE_HSTS_SECONDS = 60 * 60 * 24
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SESSION_COOKIE_SECURE = USING_TUNNEL
    CSRF_COOKIE_SECURE = USING_TUNNEL
    SESSION_COOKIE_SAMESITE = "None" if USING_TUNNEL else "Lax"
    CSRF_COOKIE_SAMESITE = "None" if USING_TUNNEL else "Lax"

# --- Custom user model ---
AUTH_USER_MODEL = "users.User"

# --- i18n / timezone ---
LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_TZ = True
USE_I18N = True
USE_L10N = True

# --- Static & media ---
USE_VOLUME_MEDIA = env.bool("USE_VOLUME_MEDIA", default=False)

MEDIA_URL = "/media/"
if USE_VOLUME_MEDIA:
    MEDIA_ROOT = "/data/media"
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# --- WhiteNoise helpers (used in PROD) ---
def whitenoise_immutable_test(path, url):

    filename = path.rsplit("/", 1)[-1]
    return bool(re.search(r"\.[0-9a-f]{8,}\.", filename))

def whitenoise_add_headers(headers, path, url):
    # WhiteNoise already sets max-age; complement with SWR if immutable
    if whitenoise_immutable_test(path, url):
        headers["Cache-Control"] = "public, max-age=31536000, immutable, stale-while-revalidate=86400"

# ---- WhiteNoise per environment ----
if DEBUG:
    # DEV: sin manifest, sin caché, recarga al vuelo y finders
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    WHITENOISE_AUTOREFRESH = True
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_MAX_AGE = 0
    WHITENOISE_ADD_HEADERS_FUNCTION = None
else:
    # PROD: manifest + caché larga solo para archivos con hash
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # 1 año
    WHITENOISE_IMMUTABLE_FILE_TEST = whitenoise_immutable_test
    WHITENOISE_ADD_HEADERS_FUNCTION = whitenoise_add_headers

LOGIN_URL = reverse_lazy("users:login")
LOGIN_REDIRECT_URL = reverse_lazy("users:profile")
LOGOUT_REDIRECT_URL = "/"

# --- reCAPTCHA v3 ---
RECAPTCHA_SITE_KEY = env("RECAPTCHA_SITE_KEY", default="")
RECAPTCHA_SECRET_KEY = env("RECAPTCHA_SECRET_KEY", default="")
RECAPTCHA_MIN_SCORE = env.float("RECAPTCHA_MIN_SCORE", default=0.5)

# --- django-axes basic config ---
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_TEMPLATE = 'errors/locked_out.html'


# --- Default PK field ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
