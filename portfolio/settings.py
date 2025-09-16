from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from pathlib import Path
import os
import environ


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializa django-environ
env = environ.Env(
    DEBUG=(bool, False)  
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))  

# Configuración de seguridad
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')  


# Configuración de Pi Payments
PI_API_KEY = env("PI_API_KEY")



# Application definition
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',
    'projects',
    'services',
    'pi_payments',
    'users.apps.UsersConfig',
    'orders',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'portfolio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS':  [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'portfolio.wsgi.application'


# DN CONFIG
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE'),  
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'OPTIONS': {
             'charset': 'utf8mb4',
             'init_command': "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",
        },
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Email backend (consola para desarrollo)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# UNFOLD CONFIG
UNFOLD = {
    # Títulos
    "SITE_TITLE": "Portfolio Admin",
    "SITE_HEADER": "José Admin",
    "SITE_SUBHEADER": "Developer Dashboard",
    "SITE_URL": "/",

    # Icono y logotipo (light/dark)
    "SITE_ICON": {
        "light": lambda request: static("img/admin/icon-light.svg"),
        "dark": lambda request: static("img/admin/icon-dark.svg"),
    },
    "SITE_LOGO": {
        "light": lambda request: static("img/admin/logo-light.png"),
        "dark": lambda request: static("img/admin/jf_logo.png"),
    },
    "SITE_SYMBOL": "code",  # Material Symbols name

    # Favicons (puedes añadir más tamaños si quieres)
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("img/admin/icon-light.svg"),
        },
    ],

    # Botones superiores
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": False,

    # Tema (deja comentado para permitir el switcher)
    # "THEME": "dark",  # o "light" para forzar

    # Login
    "LOGIN": {
        "image": lambda request: static("img/admin/login-bg.svg"),
        # redirige al listado que más uses
        "redirect_after": lambda request: reverse_lazy("admin:projects_project_changelist"),
    },

    # Colores (primario morado, base gris). Ajusta si quieres tu paleta
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

    # Sidebar de navegación rápida
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

    # Dashboard: puedes inyectar variables si luego personalizas templates
    "DASHBOARD_CALLBACK": "portfolio.admin_dashboard.dashboard_callback",
}


# Custom User Model
AUTH_USER_MODEL = 'users.User'

# LANG CONFIG
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_TZ = True
USE_I18N = True
USE_L10N = True


LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = '/'  
LOGOUT_REDIRECT_URL = '/'

# Static files (CSS, JavaScript, Images)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT     = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
