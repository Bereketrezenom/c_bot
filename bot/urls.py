"""
URL configuration for bot app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('cases/', views.get_all_cases, name='get_cases'),
    path('users/', views.get_all_users, name='get_users'),
    path('assign-role/', views.assign_user_role, name='assign_role'),
    path('stats/', views.get_stats, name='stats'),
]

