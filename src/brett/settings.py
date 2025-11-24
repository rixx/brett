import os
from pathlib import Path

from django.contrib.messages import constants as messages
from django.utils.crypto import get_random_string

DEBUG = True

## DIRECTORY SETTINGS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BRETT_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = DATA_DIR / "logs"
MEDIA_ROOT = DATA_DIR / "media"
STATIC_ROOT = BASE_DIR / "static.dist"

for directory in (DATA_DIR, LOG_DIR, MEDIA_ROOT):
    directory.mkdir(parents=True, exist_ok=True)

## APP SETTINGS
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "brett.core",
]

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
TIME_ZONE = os.environ.get("BRETT_TIME_ZONE", "Europe/Berlin")
LANGUAGE_COOKIE_NAME = "brett_language"

## MIDDLEWARE SETTINGS
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
