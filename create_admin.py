"""
Script to create or set admin password.
Run this: python create_admin.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'counseling_bot.settings')
django.setup()

from django.contrib.auth.models import User

def set_admin_password():
    # Set admin password
    try:
        user = User.objects.get(username='admin')
        user.set_password('admin123')
        user.save()
        print("\nSuccess: Admin password set successfully!")
        print("\nYour Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\nAccess URLs:")
        print("   Admin Login: http://localhost:8000/admin/")
        print("   Cases Dashboard: http://localhost:8000/admin/counseling/")
    except User.DoesNotExist:
        # Create admin if doesn't exist
        User.objects.create_superuser(username='admin', email='admin@example.com', password='admin123')
        print("\nSuccess: Admin user created!")
        print("\nYour Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")

if __name__ == '__main__':
    set_admin_password()

