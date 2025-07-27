from backend.settings.base import *
from django.core.exceptions import ImproperlyConfigured

load_dotenv(os.path.join(BASE_DIR, '.env.prod'))

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


DEBUG = False # Toujours False en production !


if not ALLOWED_HOSTS :#or ALLOWED_HOSTS == ['*']:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be explicitly set in production.")

# DATABASES = { # Valeur par défaut, sera écrasée
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': "/var/app/current/db_prod.sqlite3",
#     }
# }


# if os.environ.get('RDS_HOSTNAME'): # Vérifie si les variables RDS sont fournies par EB
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql', # Assurez-vous que c'est bien postgresql
#             'NAME': os.environ.get('RDS_DB_NAME'),
#             'USER': os.environ.get('RDS_USERNAME'),
#             'PASSWORD': os.environ.get('RDS_PASSWORD'),
#             'HOST': os.environ.get('RDS_HOSTNAME'),
#             'PORT': os.environ.get('RDS_PORT', '5432'),
#         }
#     }
# else:
#     # Configuration de fallback (par exemple, pour un test local de la config de prod avec SQLite,
#     # mais idéalement, ceci ne devrait pas être atteint sur EB si RDS est configuré)
#     print("WARNING: RDS environment variables not found. Falling back to local DB config for production settings.")
#     raise ImproperlyConfigured("WARNING: RDS environment variables not found.")

#     # DATABASES = {
#     #     'default': {
#     #         'ENGINE': 'django.db.backends.sqlite3',
#     #         'NAME': os.path.join(BASE_DIR, 'db_prod_fallback.sqlite3'),
#     #     }
#     # }


# # Vérification que les variables de DB de prod sont bien présentes
# if not all([DATABASES['default']['ENGINE'], DATABASES['default']['NAME'], DATABASES['default']['USER'],
#             DATABASES['default']['PASSWORD'], DATABASES['default']['HOST'], DATABASES['default']['PORT']]):
#     raise ImproperlyConfigured("Production database settings are incomplete.")


# --- Fichiers Statiques et Médias en Production (S3) ---
if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STATIC_BUCKET_NAME, AWS_MEDIA_BUCKET_NAME]):
    raise ImproperlyConfigured("AWS credentials/bucket names missing for production.")

AWS_LOCATION_STATIC = 'static'
AWS_S3_CUSTOM_DOMAIN_STATIC = os.environ.get('AWS_S3_CLOUDFRONT_STATIC_DOMAIN', f'{AWS_STATIC_BUCKET_NAME}.s3.amazonaws.com') # Utilisez un domaine CloudFront ici
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN_STATIC}/{AWS_LOCATION_STATIC}/'
STATICFILES_STORAGE = 'backend.storages.StaticStorage'

AWS_LOCATION_MEDIA = 'media'
AWS_S3_CUSTOM_DOMAIN_MEDIA = os.environ.get('AWS_S3_CLOUDFRONT_MEDIA_DOMAIN', f'{AWS_MEDIA_BUCKET_NAME}.s3.amazonaws.com') # Utilisez un domaine CloudFront ici
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN_MEDIA}/{AWS_LOCATION_MEDIA}/'
DEFAULT_FILE_STORAGE = 'backend.storages.MediaStorage'


# --- CORS pour la Production ---
_prod_cors_origins_str_from_env = os.environ.get('PROD_CORS_ALLOWED_ORIGINS', '') # Relit car il était dans base
if not _prod_cors_origins_str_from_env:
     raise ImproperlyConfigured("PROD_CORS_ALLOWED_ORIGINS must be set in production.")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _prod_cors_origins_str_from_env.split(',') if origin.strip()]

_prod_csrf_origins_str_from_env = os.environ.get('PROD_CSRF_TRUSTED_ORIGINS', '')
if not _prod_csrf_origins_str_from_env:
    raise ImproperlyConfigured("PROD_CSRF_TRUSTED_ORIGINS must be set in production for CSRF protection.")
CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in _prod_csrf_origins_str_from_env.split(',') if origin.strip()])


# --- Email pour la Production ---
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND_PROD', 'django.core.mail.backends.smtp.EmailBackend')
# ... autres variables EMAIL_HOST, EMAIL_PORT, etc., spécifiques à la prod si différentes de base.py ...
if not all([EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL]):
     raise ImproperlyConfigured("Production email settings are incomplete.")


# --- Sécurité en Production ---
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') # Important derrière un load balancer / reverse proxy
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups" # Ou "same-origin" pour plus de sécurité

# --- Simple JWT Cookies (pour prod HTTPS) ---
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = False
SIMPLE_JWT['AUTH_COOKIE_SAMESITE'] = os.environ.get('PROD_AUTH_COOKIE_SAMESITE', 'Lax') # 'None' pour cross-site avec HTTPS


# Frontend/Backend URL checks for production
if not FRONTEND_URL or not BACKEND_URL: # FRONTEND_URL, BACKEND_URL sont lus dans base.py
    raise ImproperlyConfigured("FRONTEND_URL and BACKEND_URL must be set in production environment variables.")

# Vérifications PayDunya spécifiques à la production
PAYDUNYA_LIVE_KEYS_FROM_ENV = { # Relire ici si vous voulez une vérification stricte pour la prod
    'PAYDUNYA-MASTER-KEY': os.environ.get("PAYDUNYA_LIVE_MASTER_KEY", ""),
    'PAYDUNYA-PRIVATE-KEY': os.environ.get("PAYDUNYA_LIVE_PRIVATE_KEY", ""),
    'PAYDUNYA-PUBLIC-KEY': os.environ.get("PAYDUNYA_LIVE_PUBLIC_KEY", ""),
    'PAYDUNYA-TOKEN': os.environ.get("PAYDUNYA_LIVE_TOKEN", ""),
}
if PAYDUNYA_DEBUG is False and not all(PAYDUNYA_LIVE_KEYS_FROM_ENV.values()): # PAYDUNYA_DEBUG vient de base.py
    missing_keys = [k for k, v in PAYDUNYA_LIVE_KEYS_FROM_ENV.items() if not v]
    raise ImproperlyConfigured(f"PayDunya LIVE keys missing in environment for production: {', '.join(missing_keys)}")


WEBPACK_LOADER['DEFAULT']['CACHE'] = True
WEBPACK_LOADER['DEFAULT']['BUNDLE_DIR_NAME'] = '' # Ou le sous-dossier sur S3/CloudFront où les assets React sont, si STATIC_URL est la racine du CDN.

# `STATS_FILE` doit pointer vers le fichier généré par le build de production
WEBPACK_LOADER['DEFAULT']['STATS_FILE'] = os.path.join(BASE_DIR, 'webpack-stats.json') 
# --- django-webpack-loader (QUAND VOUS L'INTÉGREREZ) ---
# WEBPACK_LOADER = {
#     'DEFAULT': {
#         'CACHE': True, # Cache en prod
#         'BUNDLE_DIR_NAME': 'frontend/', # Relatif à STATIC_ROOT pour les builds collectés
#         'STATS_FILE': os.path.join(BASE_DIR, 'frontend/webpack-stats-production.json'), # Nom de fichier différent pour les stats de prod
#         # Pas de POLL_INTERVAL en prod
#         'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
#     }
# }

# Logging configuration (important for production)
# LOGGING = { ... } # Ajoutez une configuration de logging robuste

if not all(active_keys_to_check.values()):
    missing_keys = [k for k, v in active_keys_to_check.items() if not v]
    env_type = "DEBUG" if PAYDUNYA_DEBUG else "LIVE"
    raise ImproperlyConfigured(f"PayDunya {env_type} keys missing in environment: {', '.join(missing_keys)}")