import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME = BASE_DIR / "runtime"
RUNTIME.mkdir(exist_ok=True)
DEBUG = os.environ.get("GROCERY_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("GROCERY_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("GROCERY_SECRET_KEY is required when DEBUG is disabled")
    secret_file = RUNTIME / ".development-secret"
    try:
        with secret_file.open("x") as output:
            output.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    SECRET_KEY = secret_file.read_text()
ALLOWED_HOSTS = os.environ.get("GROCERY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
CSRF_TRUSTED_ORIGINS = [s for s in os.environ.get("GROCERY_CSRF_ORIGINS", "").split(",") if s]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "accounts", "catalog", "orders", "operations",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.RequestLogMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
if os.environ.get("GROCERY_DB_ENGINE") == "postgres":
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "grocery"), "USER": os.environ.get("PGUSER", "grocery"),
        "PASSWORD": os.environ["PGPASSWORD"], "HOST": os.environ.get("PGHOST", "127.0.0.1"),
        "PORT": os.environ.get("PGPORT", "5432")}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("GROCERY_DB_PATH", str(RUNTIME / "grocery.sqlite3")),
        "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"}}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-ca"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = RUNTIME / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "stores"
LOGOUT_REDIRECT_URL = "stores"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
LOCAL_SANDBOX = os.environ.get("GROCERY_LOCAL_SANDBOX") == "1"
SESSION_COOKIE_SECURE = not DEBUG and not LOCAL_SANDBOX
CSRF_COOKIE_SECURE = not DEBUG and not LOCAL_SANDBOX
SECURE_SSL_REDIRECT = not DEBUG and not LOCAL_SANDBOX
SECURE_HSTS_SECONDS = 31536000 if not DEBUG and not LOCAL_SANDBOX else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(SECURE_HSTS_SECONDS)
SECURE_HSTS_PRELOAD = bool(SECURE_HSTS_SECONDS)
if os.environ.get("GROCERY_TRUST_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "loggers": {"grocery.events": {"handlers": ["console"], "level": "INFO", "propagate": False}}}
NODE_NAME = os.environ.get("GROCERY_NODE", "web-local")
RESERVATION_SECONDS = int(os.environ.get("GROCERY_RESERVATION_SECONDS", "900"))
PAYMENT_URL = os.environ.get("GROCERY_PAYMENT_URL", "http://127.0.0.1:9000")
PAYMENT_TOKEN = os.environ.get("GROCERY_PAYMENT_TOKEN", "")
PAYMENT_TIMEOUT = float(os.environ.get("GROCERY_PAYMENT_TIMEOUT", "1"))
if not NODE_NAME or len(NODE_NAME) > 64 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in NODE_NAME):
    raise RuntimeError("Invalid GROCERY_NODE")
LOG_INDEX_PATH = Path(os.environ.get("GROCERY_LOG_INDEX", str(RUNTIME / "events.sqlite")))
if os.environ.get("GROCERY_LOG_DIR"):
    log_dir = Path(os.environ["GROCERY_LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    LOGGING["handlers"]["events_file"] = {
        "class": "logging.handlers.RotatingFileHandler", "filename": str(log_dir / f"{NODE_NAME}.jsonl"),
        "maxBytes": 10485760, "backupCount": 3, "encoding": "utf-8"}
    LOGGING["loggers"]["grocery.events"]["handlers"].append("events_file")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PUBLIC_BASE_URL = os.environ.get("GROCERY_PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
if STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_test_"):
    raise RuntimeError("Only Stripe test-mode keys are accepted")
OFF_USER_AGENT = os.environ.get("OFF_USER_AGENT", "GroceryArchitectureLab/1.0 (https://github.com/Daatari/grocery-store-management)")
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144
