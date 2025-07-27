# settings/local.py
from backend.settings.base import *
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

DEBUG = True

ALLOWED_HOSTS = ['*']



# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db_prod_fallback.sqlite3'),
#     }
# }


# --- CORS pour le développement ---
_dev_cors_origins_str = os.environ.get('DEV_CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _dev_cors_origins_str.split(',') if origin.strip()]
if NGROK_DOMAIN_ENV:
    CORS_ALLOWED_ORIGINS.append(NGROK_DOMAIN_ENV)

CSRF_TRUSTED_ORIGINS.append('http://localhost:3000')
CSRF_TRUSTED_ORIGINS.append('http://127.0.0.1:3000')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SIMPLE_JWT['AUTH_COOKIE_SECURE'] = False
SIMPLE_JWT['AUTH_COOKIE_SAMESITE'] = 'Lax'



STATIC_URL = STATIC_URL_BASE # Ou directement '/static/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
MEDIA_URL = MEDIA_URL_BASE # Ou directement '/media/'
MEDIA_ROOT = MEDIA_ROOT_BASE # Ou directement BASE_DIR / 'media'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


if 'webpack_loader' in INSTALLED_APPS : # Vérifie si webpack_loader est bien dans les apps installées
    WEBPACK_LOADER.setdefault('DEFAULT', {}) # Assure que 'DEFAULT' existe
    WEBPACK_LOADER['DEFAULT']['CACHE'] = not DEBUG
    WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = os.path.join(BASE_DIR.parent, 'frontend/webpack-stats.json')
    WEBPACK_LOADER['DEFAULT']['POLL_INTERVAL'] = 0.1 # Vérifie les changements toutes les 0.1s
