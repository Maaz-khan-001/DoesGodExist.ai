from .base import *

DEBUG = True

# Allow more origins in development
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:5175',
    'http://127.0.0.1:5173',
]

# Email: print to console in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# JWT cookie: don't require HTTPS in dev
REST_AUTH = {
    **REST_AUTH,
    'JWT_AUTH_SECURE': False,
}

# Relax Axes in development (don't lock out devs)
AXES_ENABLED = False

# Show all SQL queries in development (optional, very verbose)
# LOGGING['loggers']['django.db.backends'] = {
#     'handlers': ['console'], 'level': 'DEBUG', 'propagate': False
# }