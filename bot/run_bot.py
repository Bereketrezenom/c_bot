"""
Simple standalone bot runner.
"""
import logging
import os


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


def main() -> None:
    # Ensure Django settings module is set when running outside manage.py
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'counseling_bot.settings')
    from bot.bot_app.app import run as run_app
    run_app()


if __name__ == '__main__':
    main()


