from django.apps import AppConfig


class MessengerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messenger'
    verbose_name = 'Мессенджер'

    def ready(self):
        # Connect event bus signal handlers
        from messenger.infrastructure.event_bus import connect_signals
        connect_signals()
