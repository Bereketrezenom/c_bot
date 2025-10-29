#!/usr/bin/env python
"""
Simple script to run Django and bot together.
"""
import os
import sys
import subprocess
import threading


def run_django():
    """Run Django development server."""
    os.system("python manage.py runserver")


def run_bot():
    """Run Telegram bot."""
    os.system("python manage.py run_bot")


if __name__ == '__main__':
    print("Starting Counseling Bot...")
    print("Press Ctrl+C to stop")
    
    # Create threads
    django_thread = threading.Thread(target=run_django)
    bot_thread = threading.Thread(target=run_bot)
    
    # Start threads
    django_thread.daemon = True
    bot_thread.daemon = True
    
    django_thread.start()
    bot_thread.start()
    
    # Wait for threads
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopping services...")
        sys.exit(0)

