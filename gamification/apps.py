from django.apps import AppConfig


class GamificationConfig(AppConfig):
    name = 'gamification'

    def ready(self):
        from . import signals  # noqa: F401 — XP signallarini ulash
