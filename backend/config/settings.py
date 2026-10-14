"""
Django settings for the StormRoute API.

Every deploy-specific value comes from the environment (or `backend/.env`),
read through django-environ. See `.env.example` for the full list.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:5173', 'http://127.0.0.1:5173']),
    ORS_API_KEY=(str, ''),
    DATA_MODE=(str, 'live'),
    DEMO_FALLBACK=(bool, True),
    PROVIDER_TIMEOUT_S=(float, 8.0),
    RESULT_TTL_S=(int, 3600),
    LOG_LEVEL=(str, 'INFO'),
    ANALYZE_RATE=(str, '30/min'),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-only-change-me')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition
# No models: results live in the cache. auth/contenttypes stay because DRF imports them.

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.common',
    'apps.trips',
    'apps.routing',
    'apps.weather',
    'apps.risk',
    'apps.recommendations',
    'apps.demo',
    'apps.locations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'stormroute',
        'OPTIONS': {'MAX_ENTRIES': 500},
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True

STATIC_URL = 'static/'


# REST framework: JSON in, JSON out, one error shape

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.handler',
    'DEFAULT_THROTTLE_RATES': {'analyze': env('ANALYZE_RATE')},
}

CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')


# StormRoute

STORMROUTE = {
    'ORS_API_KEY': env('ORS_API_KEY'),
    # `demo` never calls providers; `live` does, and falls back to fixtures if DEMO_FALLBACK
    'DATA_MODE': env('DATA_MODE'),
    'DEMO_FALLBACK': env('DEMO_FALLBACK'),
    'PROVIDER_TIMEOUT_S': env('PROVIDER_TIMEOUT_S'),
    'RESULT_TTL_S': env('RESULT_TTL_S'),
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'stormroute': {'handlers': ['console'], 'level': env('LOG_LEVEL'), 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'WARNING'},
    },
}


if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True
