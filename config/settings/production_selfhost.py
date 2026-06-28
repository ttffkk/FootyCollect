# ruff: noqa: E501, F403, F405
"""Self-hosted production settings.

Built for running FootyCollect on your own box behind a reverse proxy
(Cloudflare Tunnel -> nginx) instead of the maintainer's SaaS. It deliberately
does NOT inherit from ``production`` because that module hard-requires object
storage (S3/R2), Sentry and SendGrid and calls ``sentry_sdk.init`` at import
time. Here we build on ``base`` and re-add only the hardening we want:

- Static files served by WhiteNoise from inside the container (no S3/R2).
- Media (user-uploaded photos) on the local filesystem (a Docker volume).
- Email to the console (no transactional provider).
- TLS terminated upstream; this app speaks http and trusts X-Forwarded-Proto.
"""

from .base import *  # noqa: F401
from .base import INSTALLED_APPS, MIDDLEWARE, env

# GENERAL
# ------------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["footy.ttffkk.com"])

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# CACHES (Redis)
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

# SECURITY
# ------------------------------------------------------------------------------
# TLS is terminated at the edge (Cloudflare); nginx forwards the original
# scheme so Django still treats the request as secure for cookies/CSRF.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# The tunnel already forces https at the edge and the internal hop is http, so
# in-app redirects are off by default (toggle with the env var if desired).
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
SESSION_COOKIE_NAME = "__Secure-sessionid" if SESSION_COOKIE_SECURE else "sessionid"
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
CSRF_COOKIE_NAME = "__Secure-csrftoken" if CSRF_COOKIE_SECURE else "csrftoken"
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[f"https://{h}" for h in ALLOWED_HOSTS if h and "*" not in h],
)

# STATIC (WhiteNoise) & MEDIA (local filesystem)
# ------------------------------------------------------------------------------
# Serve collected static straight from the app container; no object storage.
# WhiteNoise must sit right after the security middleware.
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )
STORAGES = {
    # Media: user uploads land on a local volume (MEDIA_ROOT from base).
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    # Static: gzip/brotli-compressed by WhiteNoise. No hashed manifest, so a
    # missing {% static %} reference degrades instead of 500-ing the page.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
# STATIC_ROOT/STATIC_URL/MEDIA_ROOT/MEDIA_URL are inherited from base (all local).

# django-compressor
# ------------------------------------------------------------------------------
# Disabled: online compression is incompatible with a self-host static pipeline
# (it would try to write into the collected static tree at request time), and
# WhiteNoise already compresses. {% compress %} blocks fall back to raw links.
COMPRESS_ENABLED = env.bool("COMPRESS_ENABLED", default=False)

# EMAIL
# ------------------------------------------------------------------------------
# No transactional provider self-hosted; print to the container log by default.
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="footycollect <noreply@footy.ttffkk.com>",
)
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[footycollect] ")

# ADMIN
# ------------------------------------------------------------------------------
# base.py defaults this to "admin/"; allow an env override to obscure it.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# Football Kit Archive API (self-hosted fkapi)
# ------------------------------------------------------------------------------
# FKA_API_IP and API_KEY are already read (required) in base.py; they point at
# the internal fkapi service over the docker network.
