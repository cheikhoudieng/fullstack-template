from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

DEBUG = os.environ.get('DEBUG', 'True') == 'True' 


BASE_DIR = Path(__file__).resolve().parent.parent.parent
# load_dotenv(os.path.join(BASE_DIR, '.env.prod'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key-if-not-set')

DEBUG_ENV_VAR = os.environ.get('DEBUG', 'True')

ALLOWED_HOSTS_STR = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()]

NGROK_DOMAIN_ENV = os.environ.get('NGROK_DOMAIN')
if NGROK_DOMAIN_ENV:
    ALLOWED_HOSTS.append(NGROK_DOMAIN_ENV)

if DEBUG:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.local')
    load_dotenv(os.path.join(BASE_DIR, '.env'))


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Assurez-vous que c'est bien postgresql
        'NAME': os.environ.get('RDS_DB_NAME'),
        'USER': os.environ.get('RDS_USERNAME'),
        'PASSWORD': os.environ.get('RDS_PASSWORD'),
        'HOST': os.environ.get('RDS_HOSTNAME'),
        'PORT': os.environ.get('RDS_PORT', '5432'),
    }
}


# --- AWS Credentials & Bucket Names ---
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
# ... (tous vos paramètres AWS S3 communs, y compris les noms de bucket, région, endpoint) ...
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', None)
AWS_STATIC_BUCKET_NAME = os.environ.get('AWS_STATIC_BUCKET_NAME', '')
AWS_MEDIA_BUCKET_NAME = os.environ.get('AWS_MEDIA_BUCKET_NAME', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')




PYTHONANYWHERE_DOMAIN = os.environ.get('PYTHONANYWHERE_DOMAIN')
FRONTEND_URL = os.environ.get('FRONTEND_URL')
BACKEND_URL = os.environ.get('BACKEND_URL')


CSRF_TRUSTED_ORIGINS = []
if NGROK_DOMAIN_ENV: 
    CSRF_TRUSTED_ORIGINS.append(NGROK_DOMAIN_ENV)

_prod_csrf_origins_str = os.environ.get('PROD_CSRF_TRUSTED_ORIGINS', '') # Ce sera géré par production.py
PASSWORD_RESET_TIMEOUT_HOURS = 1


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'DEFAULT_PARSER_CLASSES': ('rest_framework.parsers.JSONParser',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'user_auth.authentication.CookieJWTAuthentication',
        # 'rest_framework_simplejwt.authentication.JWTAuthentication', # Keep Cookie auth
    ),
    # 'DEFAULT_THROTTLE_CLASSES': [ ... ], # Uncomment if needed
    # 'DEFAULT_THROTTLE_RATES': { ... }
}

INSTALLED_APPS = [
    'django.contrib.sitemaps',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'core',
    'user_auth',
    'rest_framework',
    'corsheaders',
    'ia_manager',
    'dynamic_forms',
    'webpack_loader',
    'seo',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Positioned high
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt',
    'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'template'],
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
WSGI_APPLICATION = 'backend.wsgi.application' 


# DATABASES (sera surchargé dans local et production)
# DATABASES = { # Valeur par défaut, sera écrasée
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'user_auth.User'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN' # If using CSRF with AJAX

# --- Email Configuration ---
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
_admin_emails_str = os.environ.get('ADMIN_EMAIL_RECIPIENTS', '')
ADMIN_EMAIL_RECIPIENTS = [email.strip() for email in _admin_emails_str.split(',') if email.strip()]
ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'True') == 'True'
ENABLE_NOTIFICATIONS = True

APPEND_SLASH = False

AUTHENTICATION_BACKENDS = [
    'user_auth.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
]

# --- Social Auth ---
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']



PAYDUNYA_DEBUG = os.environ.get('PAYDUNYA_DEBUG', 'True') == 'True'

PAYDUNYA_KEYS_DEBUG = {
    'PAYDUNYA-MASTER-KEY': os.environ.get("PAYDUNYA_DEBUG_MASTER_KEY", ""),
    'PAYDUNYA-PRIVATE-KEY': os.environ.get("PAYDUNYA_DEBUG_PRIVATE_KEY", ""),
    'PAYDUNYA-PUBLIC-KEY': os.environ.get("PAYDUNYA_DEBUG_PUBLIC_KEY", ""),
    'PAYDUNYA-TOKEN': os.environ.get("PAYDUNYA_DEBUG_TOKEN", ""),
}
PAYDUNYA_KEYS_LIVE = {
    'PAYDUNYA-MASTER-KEY': os.environ.get("PAYDUNYA_LIVE_MASTER_KEY", ""),
    'PAYDUNYA-PRIVATE-KEY': os.environ.get("PAYDUNYA_LIVE_PRIVATE_KEY", ""),
    'PAYDUNYA-PUBLIC-KEY': os.environ.get("PAYDUNYA_LIVE_PUBLIC_KEY", ""),
    'PAYDUNYA-TOKEN': os.environ.get("PAYDUNYA_LIVE_TOKEN", ""),
}
active_keys_to_check = PAYDUNYA_KEYS_DEBUG if PAYDUNYA_DEBUG else PAYDUNYA_KEYS_LIVE





store_name_env = os.environ.get('PAYDUNYA_STORE_NAME', "Cicaw")
if PAYDUNYA_DEBUG:
    store_name_env += " (TEST)"



logo_url = "https://cicaw-static-assets.s3.amazonaws.com/static/images/cicaw.png"

PAYDUNYA_STORE_INFO = {
    'name': store_name_env,
    'tagline':  os.environ.get('PAYDUNYA_STORE_TAGLINE', "Votre e-commerce"),
    'postal_address': os.environ.get('PAYDUNYA_STORE_POSTAL_ADDRESS', "Dakar, Sénégal"),
    'phone_number': os.environ.get('PAYDUNYA_STORE_PHONE_NUMBER', "+221xxxxxxxxx"),
    'website_url': FRONTEND_URL, # Link to user-facing site
    'logo_url': os.environ.get('PAYDUNYA_STORE_LOGO_URL', ''),
    'return_url': f'{BACKEND_URL}/api/payments/paydunya/success/', # Adjust path as needed
    'cancel_url': f'{BACKEND_URL}/api/payments/paydunya/cancel/', # Adjust path as needed
    'callback_url': f'{BACKEND_URL}/api/payments/paydunya/ipn/',   # Adjust path as needed (IPN Handler)
}

PAYDUNYA = {
    "PAYDUNYA_DEBUG": PAYDUNYA_DEBUG,
    "KEY": active_keys_to_check,
    "STORE": PAYDUNYA_STORE_INFO,
}

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# settings.py
SITE_NAME =  'Cicaw Marketplace'

SEO_SETTINGS = {
    'DEFAULT_TITLE': os.environ.get('SEO_DEFAULT_TITLE', 'Titre par défaut'),
    'TITLE_TEMPLATE': f'%s | {os.environ.get("SEO_ORGANIZATION_NAME", "Cicaw")}',
    'DEFAULT_DESCRIPTION': os.environ.get('SEO_DEFAULT_DESCRIPTION', 'Description par défaut'),
    'DEFAULT_OG_IMAGE': os.environ.get('SEO_DEFAULT_OG_IMAGE', ''),
    'DEFAULT_OG_TYPE': 'website',
    'SITE_NAME': os.environ.get("SEO_ORGANIZATION_NAME", 'Cicaw'),
    'TWITTER_SITE': os.environ.get('SEO_TWITTER_SITE', ''),
    'DEFAULT_TWITTER_CARD': 'summary_large_image',
    'DEFAULT_ROBOTS': 'index, follow',
    'DEFAULT_LOCALE': 'fr_SN',
    'DEFAULT_CURRENCY': 'XOF',
    'JSONLD_DEFAULT_ORGANIZATION': {
        '@type': 'Organization',
        'name': os.environ.get('SEO_ORGANIZATION_NAME', 'Cicaw'),
        'url': os.environ.get('SEO_ORGANIZATION_URL', ''),
        'logo': os.environ.get('SEO_ORGANIZATION_LOGO', ''),
        'description': os.environ.get('SEO_ORGANIZATION_DESCRIPTION', ''),
        'address': {
            '@type': 'PostalAddress',
            'addressCountry': 'SN'
        },
        'contactPoint': [
            {
                '@type': 'ContactPoint',
                'telephone': '+221772849433',
                'contactType': 'customer service',
                'areaServed': 'SN', 
                'availableLanguage': ['French'] 
            }
        ],
        'sameAs': [
           "https://www.tiktok.com/@cicaw.com?is_from_webapp=1&sender_device=pc",
            "https://www.instagram.com/cicawcom/",
            "https://www.facebook.com/profile.php?id=61559292953669",
            "https://youtube.com/@cicawcom?si=DU8YL-dRL6dYeGzf",
            "https://x.com/CicawCom"
        ]
    },
}
# SEO_SETTINGS['JSONLD_DEFAULT_ORGANIZATION']['sameAs'] = [
#     url for url in SEO_SETTINGS['JSONLD_DEFAULT_ORGANIZATION']['sameAs'] if url
# ]



STATIC_URL_BASE = '/static/' # Un nom générique si besoin, sera surchargé
STATIC_ROOT = BASE_DIR / 'collected_static'
STATICFILES_DIRS = [ os.path.join(BASE_DIR, 'template/build/static')] # Si ce chemin est commun
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
MEDIA_URL_BASE = '/media/' # Sera surchargé
MEDIA_ROOT_BASE = BASE_DIR / 'media' # Sera surchargé ou utilisé pour le chemin


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',

    # --- Cookie Specific Settings ---
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_DOMAIN': os.environ.get('AUTH_COOKIE_DOMAIN', None),
    # 'AUTH_COOKIE_SECURE': True, # True in Production (HTTPS), False in Development
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    # Use 'None' for prod cross-site (requires Secure=True), 'Lax' for dev/same-site.
    'AUTH_COOKIE_SAMESITE': os.environ.get('AUTH_COOKIE_SAMESITE_DEFAULT', 'Lax'), # Une valeur par défaut

}

WEBPACK_LOADER = {
    'DEFAULT': {
        # Le chemin vers le fichier de statistiques généré par webpack-bundle-tracker
        # Ce chemin est relatif à BASE_DIR (racine de votre projet Django 'backend/')
        # Si frontend est un dossier frère de backend/ :
        'CACHE': False, # Important pour le dev

        'STATS_FILE': os.path.join(BASE_DIR.parent, 'frontend/webpack-stats.json'),
        # Si frontend est DANS backend/:
        # 'STATS_FILE': os.path.join(BASE_DIR, 'frontend/webpack-stats.json'),

        'POLL_INTERVAL': 0.1, # Utile en dev pour le rechargement à chaud
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map'],
        'LOADER_CLASS': 'webpack_loader.loader.WebpackLoader',
        
    }
}

DEFAULT_AI_PROVIDER = "gemini"