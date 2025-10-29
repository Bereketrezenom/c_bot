"""
Django signals for bot app.
"""
from django.db.models.signals import post_migrate
from django.dispatch import receiver
import threading


@receiver(post_migrate)
def start_bot(sender, **kwargs):
    """Start the Telegram bot after Django migrations."""
    if sender.name == 'bot':
        from .telegram_bot import CounselingBot
        import os
        
        if os.getenv('START_BOT_ON_LOAD', 'False') == 'True':
            bot = CounselingBot()
            thread = threading.Thread(target=bot.run, daemon=True)
            thread.start()

