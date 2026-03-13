"""
ASGI config for DoesGodExist.ai

Exposes the ASGI callable as module-level variable named `application`.
Required for:
  - Server-Sent Events (SSE) streaming in views_stream.py
  - Django Channels (if added later)

Production server:
  gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -w 4

Development:
  uvicorn config.asgi:application --reload --port 8000
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'config.settings.development'
)

application = get_asgi_application()
