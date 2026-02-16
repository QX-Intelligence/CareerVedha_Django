from pathlib import Path
import os
import textwrap
from dotenv import load_dotenv

# -------------------------------------------------
# BASE
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# -------------------------------------------------
# CORE DJANGO
# -------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

# ALLOWED HOSTS
_allowed_hosts = []
for i in range(1, 10):  # Support up to 9 hosts
    host = os.getenv(f"DJANGO_ALLOWED_HOSTS_{i}")
    if host:
        _allowed_hosts.append(host)

# Fallback to comma-separated list if no numbered hosts
if not _allowed_hosts:
    raw_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
    if raw_hosts == "*" or raw_hosts == "":
        _allowed_hosts = ["*"]
    else:
        _allowed_hosts = raw_hosts.replace(" ", "").split(",")

ALLOWED_HOSTS = _allowed_hosts

# -------------------------------------------------
# APPLICATIONS
# -------------------------------------------------
INSTALLED_APPS = [
    # Django core (REQUIRED)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",

    # Local apps
    "apps.common",
    "apps.taxonomy",
    "apps.articles",
    "apps.jobs",
    "apps.media",
    "apps.academics",
]

# -------------------------------------------------
# SITE ID (REQUIRED FOR SITEMAP)
# -------------------------------------------------
SITE_ID = 1

# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ Required for static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    # REQUIRED FOR ADMIN (UI ONLY)
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# -------------------------------------------------
# TEMPLATES (ADMIN / INTERNAL TOOLS ONLY)
# -------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# -------------------------------------------------
# DATABASE (SUPABASE POSTGRES)
# -------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "CONN_MAX_AGE": 0,
     
}
}

AUTH_PASSWORD_VALIDATORS = []

# Prevent Django auth usage in business logic
AUTHENTICATION_BACKENDS = []


LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "en-us")
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")

USE_I18N = True
USE_TZ = False

# -------------------------------------------------
# STATIC FILES
# -------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ WhiteNoise Storage (Compression + Caching)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# -------------------------------------------------
# MEDIA (NOT USED IN SERVICE-1)
# -------------------------------------------------
MEDIA_URL = ""
MEDIA_ROOT = ""

# -------------------------------------------------
# DJANGO REST FRAMEWORK
# -------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

# -------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# -------------------------------------------------
# Build CORS allowed origins from environment variables
_cors_origins = []
for i in range(1, 10):  # Support up to 9 origins
    origin = os.getenv(f"CORS_ALLOWED_ORIGINS_{i}")
    if origin:
        _cors_origins.append(origin)

# Fallback to comma-separated list if no numbered origins
if not _cors_origins:
    _cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    _cors_origins = [o.strip() for o in _cors_origins_str.split(",")]

CORS_ALLOWED_ORIGINS = _cors_origins
CORS_ALLOW_CREDENTIALS = True

# Parse CORS headers from environment or use defaults
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS").split(",")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Authorization,Content-Type,X-CSRF-Token,Accept,Origin").split(",")
CORS_EXPOSE_HEADERS = os.getenv("CORS_EXPOSE_HEADERS", "Content-Type,X-CSRFToken,X-Request-ID").split(",")

# -------------------------------------------------
# JWT (SPRING BOOT – VERIFY ONLY)
# IMPORTANT: Windows-safe PEM construction
# -------------------------------------------------
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")

_base64_key = os.getenv("JWT_PUBLIC_KEY_BASE64")

if _base64_key:
    JWT_PUBLIC_KEY = textwrap.dedent(f"""\
-----BEGIN PUBLIC KEY-----
{_base64_key}
-----END PUBLIC KEY-----
""")
else:
    JWT_PUBLIC_KEY = None

REDIS_URL = os.getenv("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",   
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "career_vedha_cms_service",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# -------------------------------------------------
# SECURITY HARDENING
# -------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# Hide sensitive server information
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
    "script-src": ("'self'",),
    "style-src": ("'self'", "'unsafe-inline'"),
}

# -------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# -------------------------------------------------
# SPRING BOOT NOTIFICATION SERVICE
# -------------------------------------------------
SPRING_BOOT_NOTIFICATION_URL = os.getenv("SPRING_BOOT_NOTIFICATION_URL")
SPRING_BOOT_AUTH_HEADER = os.getenv("SPRING_BOOT_AUTH_HEADER")
NOTIFICATION_TIMEOUT = int(os.getenv("NOTIFICATION_TIMEOUT"))

# -------------------------------------------------
# AWS S3 (FOR MEDIA STORAGE)
# -------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-south-2")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-2")