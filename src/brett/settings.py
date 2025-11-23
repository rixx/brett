import os
from pathlib import Path

from django.contrib.messages import constants as messages
from django.utils.crypto import get_random_string

from brett import __version__

# This settings file is structured similar to pretalx:
# Directories, Apps, Url, Security, Databases, Logging, Email, Caching (and Sessions)
# I18n, Auth, Middleware, Templates and Staticfiles

DEBUG = os.environ.get("BRETT_DEBUG", "True").lower() in ("true", "1", "yes")

## DIRECTORY SETTINGS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BRETT_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = DATA_DIR / "logs"
MEDIA_ROOT = DATA_DIR / "media"
STATIC_ROOT = BASE_DIR / "static.dist"

for directory in (DATA_DIR, LOG_DIR, MEDIA_ROOT):
    directory.mkdir(parents=True, exist_ok=True)

## APP SETTINGS
DJANGO_APPS = [
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]
EXTERNAL_APPS = []
LOCAL_APPS = [
    "brett.core",
]
INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + LOCAL_APPS

## URL SETTINGS
SITE_URL = os.environ.get("BRETT_SITE_URL", "http://localhost:8000")
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "brett.urls"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

## SECURITY SETTINGS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

CSRF_COOKIE_NAME = "brett_csrftoken"
CSRF_TRUSTED_ORIGINS = [SITE_URL]
CSRF_COOKIE_SECURE = False if DEBUG else True
CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_NAME = "brett_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = SITE_URL.startswith("https:")

SECRET_FILE = DATA_DIR / ".secret"
if SECRET_FILE.exists():
    SECRET_KEY = SECRET_FILE.read_text()
else:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    SECRET_KEY = get_random_string(50, chars)
    with SECRET_FILE.open(mode="w") as f:
        SECRET_FILE.chmod(0o600)
        f.write(SECRET_KEY)

## DATABASE SETTINGS
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        "OPTIONS": {
            "init_command": "PRAGMA synchronous=3; PRAGMA cache_size=2000;",
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

## LOGGING SETTINGS
loglevel = "DEBUG" if DEBUG else "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s %(asctime)s %(name)s %(module)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": loglevel,
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "level": loglevel,
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "brett.log",
            "formatter": "default",
        },
    },
    "loggers": {
        "": {"handlers": ["file", "console"], "level": loglevel, "propagate": True},
        "django.request": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file", "console"],
            "level": loglevel,
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

## EMAIL SETTINGS
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("BRETT_MAIL_FROM", "brett@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

## CACHE SETTINGS
CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
MESSAGE_TAGS = {
    messages.INFO: "info",
    messages.ERROR: "danger",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}

## I18N SETTINGS
USE_I18N = True
USE_TZ = True
TIME_ZONE = os.environ.get("BRETT_TIME_ZONE", "UTC")
LANGUAGE_CODE = "en-us"
LANGUAGE_COOKIE_NAME = "brett_language"

## AUTHENTICATION SETTINGS
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

## MIDDLEWARE SETTINGS
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

## TEMPLATE AND STATICFILES SETTINGS
template_loaders = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)
if not DEBUG:
    template_loaders = (("django.template.loaders.cached.Loader", template_loaders),)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            DATA_DIR / "templates",
            BASE_DIR / "templates",
        ],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": template_loaders,
        },
    }
]

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

WSGI_APPLICATION = "brett.wsgi.application"

BRETT_VERSION = __version__
if DEBUG:
    try:
        import subprocess

        BRETT_VERSION = (
            subprocess.check_output(["/usr/bin/git", "describe", "--always", "--tags"])
            .decode()
            .strip()
        )
    except Exception:
        pass
