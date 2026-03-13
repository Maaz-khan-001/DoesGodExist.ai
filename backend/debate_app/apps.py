
from django.apps import AppConfig


class DebateAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'debate_app'
    verbose_name = 'Debate'

    def ready(self):
        # Import signal handlers when app is ready
        # (add debate_app/signals.py if you add signals later)
        pass
