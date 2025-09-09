"""
Django settings for config project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
# from celery.schedules import crontab

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------ Core
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,*").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "jobs",
    "scraper",
    "api",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "dashboard" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------------ Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "jobsdb"),
        "USER": os.getenv("DB_USER", "jobsuser"),
        "PASSWORD": os.getenv("DB_PASSWORD", "jobspass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ------------------------------------------------------------------ Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------ I18N/Static
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Africa/Lagos")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "dashboard" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------ DRF & OpenAPI
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Job Scraper API",
    "VERSION": "1.0.0",
}

# ------------------------------------------------------------------ Celery schedules
SCRAPE_SCHEDULES = [
    {"source": "indeed",    "q": os.getenv("SCRAPE_Q", "Data Analyst"), "loc": os.getenv("SCRAPE_LOC", "Lagos"), "pages": int(os.getenv("SCRAPE_PAGES", "2"))},
    {"source": "glassdoor", "q": os.getenv("SCRAPE_Q", "Data Analyst"), "loc": os.getenv("SCRAPE_LOC", "Lagos"), "pages": int(os.getenv("SCRAPE_PAGES", "2"))},
    {"source": "linkedin",  "q": os.getenv("SCRAPE_Q", "Data Analyst"), "loc": os.getenv("SCRAPE_LOC", "Lagos"), "pages": int(os.getenv("SCRAPE_PAGES", "2"))},
]

# ------------------------------------------------------------------ Scraper knobs
SCRAPER_MAX_PAGES = int(os.getenv("SCRAPER_MAX_PAGES", "2"))
SCRAPER_DELAY_MS = int(os.getenv("SCRAPER_DELAY_MS", "1200"))
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "0") == "1"  # set to 0 to run visible

# ------------------------------------------------------------------ Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
