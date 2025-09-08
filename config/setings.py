import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "rest_framework","drf_spectacular",
    "jobs","scraper","api","dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND":"django.template.backends.django.DjangoTemplates",
    "DIRS":[BASE_DIR / "dashboard" / "templates"],
    "APP_DIRS":True,
    "OPTIONS":{"context_processors":[
        "django.template.context_processors.debug","django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE":"django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME","jobsdb"),
        "USER": os.getenv("DB_USER","jobsuser"),
        "PASSWORD": os.getenv("DB_PASSWORD","jobspass"),
        "HOST": os.getenv("DB_HOST","localhost"),
        "PORT": os.getenv("DB_PORT","5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE="en-us"
TIME_ZONE="UTC"
USE_I18N=True
USE_TZ=True

STATIC_URL="static/"
STATIC_ROOT=BASE_DIR / "staticfiles"
STATICFILES_DIRS=[BASE_DIR / "dashboard" / "static"]

DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"

# DRF & OpenAPI
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
SPECTACULAR_SETTINGS = {"TITLE":"Job Scraper API","VERSION":"1.0.0"}

# Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL","redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL","redis://localhost:6379/0")

# Scraper knobs
SCRAPER_MAX_PAGES = int(os.getenv("SCRAPER_MAX_PAGES","2"))
SCRAPER_DELAY_MS = int(os.getenv("SCRAPER_DELAY_MS","1200"))
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS","1") == "1"
