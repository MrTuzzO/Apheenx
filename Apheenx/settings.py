from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Application definition

INSTALLED_APPS = [
    'jazzmin',              # must be BEFORE django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    "drf_spectacular",
    'django_filters',
    'django_cleanup.apps.CleanupConfig',

    # Local
    'core',
    'user',
    'product',
    'video',
    'order',
    'wishlist',
    'announcement',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "x-csrftoken",
]

ROOT_URLCONF = 'Apheenx.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Apheenx.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(
        f"{os.getenv('DB_URL')}"
        
    )
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/


STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'user.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["core.renderers.StandardRenderer"],

    "DEFAULT_THROTTLE_RATES": {
        "user": "60/min",
        "anon": "5/min",
        "forgot_password": "3/hour",
        "resend_otp": "3/hour",
        "verify_reset_otp": "10/hour",
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 10))

REFRESH_TOKEN_COOKIE = 'refresh_token'
# REFRESH_TOKEN_COOKIE_SECURE = os.getenv('REFRESH_TOKEN_COOKIE_SECURE', str(not DEBUG)).lower() == 'true'
# REFRESH_TOKEN_COOKIE_SAMESITE = os.getenv('REFRESH_TOKEN_COOKIE_SAMESITE', 'None' if not DEBUG else 'Lax')
REFRESH_TOKEN_COOKIE_SECURE = not DEBUG          # False in dev (HTTP), True in prod (HTTPS)
REFRESH_TOKEN_COOKIE_SAMESITE = 'Lax' if DEBUG else 'None'  # Lax in dev, None in prod (cross-origin)
REFRESH_TOKEN_COOKIE_DOMAIN = os.getenv('REFRESH_TOKEN_COOKIE_DOMAIN', '')

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@apheenx.com')


CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',') if origin.strip()]

FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://10.10.12.45:3000')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
PAYPAL_WEBHOOK_ID = os.getenv('PAYPAL_WEBHOOK_ID', '')

SPECTACULAR_SETTINGS = {
    "TITLE": "Apheenx API",
    "DESCRIPTION": "API documentation",
    "VERSION": "1.0.0",
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
}


# ---------------------------------------------------------------------------
# Jazzmin — Admin UI
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Apheenx Admin",
    "site_header": "Apheenx",
    "site_brand": "Apheenx",
    "welcome_sign": "Welcome to Apheenx Admin",
    "copyright": "Apheenx",

    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["wishlist"],
    "related_modal_active": True,

    "icons": {
        "auth.Group":                 "fas fa-users-cog",
        "user.User":                  "fas fa-user-circle",
        "user.OTP":                   "fas fa-key",
        "product.ProductCategory":    "fas fa-tags",
        "product.Product":            "fas fa-box-open",
        "video.VideoCategory":        "fas fa-folder-open",
        "video.Video":                "fas fa-film",
        "video.VideoOrder":           "fas fa-shopping-cart",
        "order.Order":                "fas fa-receipt",
        "announcement.Announcement":  "fas fa-bullhorn",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    "order_with_respect_to": [
        "user", "product", "video", "order", "announcement", "auth",
    ],
}

# Keep uploads mostly on disk, not RAM
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
# Optional hard cap at app level = 1 GB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1073741824

# Stripe Settings
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# --- 기존 Media Settings (লোকাল স্টোরেজ) ---
# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- New Cloudflare R2 Settings ---

CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID', '')

# django-storages কনফিগারেশন
AWS_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Cloudflare R2 তে সাধারণত Signature Version 4 ব্যবহার হয়
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None 

# কাস্টম ডোমেইন থাকলে সেটি ব্যবহার করবে, না হলে ডিফল্ট R2 লিংক
AWS_S3_CUSTOM_DOMAIN = os.getenv('R2_CUSTOM_DOMAIN', None)

# ডিফল্ট স্টোরেজ হিসেবে S3Boto3Storage সেট করা
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# (Optional) যদি পুরনো ভার্সনের Django হয় (v4.2 এর আগের), তাহলে নিচের লাইনটি আনকমেন্ট করুন:
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'