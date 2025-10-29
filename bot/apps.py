from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'
    
    def ready(self):
        # Disable signals for now to prevent Firebase initialization during Django startup
        # import bot.signals
        pass

