"""
Management command to run the Telegram bot.
"""
from django.core.management.base import BaseCommand
import django
import os


class Command(BaseCommand):
    help = 'Run the Telegram counseling bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram Bot...'))
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'counseling_bot.settings')
        django.setup()
        
        from bot.run_bot import main
        
        try:
            main()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nBot stopped by user.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running bot: {e}'))
            raise

