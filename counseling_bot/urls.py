"""
URL configuration for counseling_bot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from bot.admin_views import admin_dashboard, api_cases, api_counselors, api_assign_case

urlpatterns = [
    # Standalone admin dashboard - accessible at /admin-ui/
    path('admin-ui/', admin_dashboard, name='admin_dashboard'),
    path('admin-ui/api/cases/', api_cases, name='api_cases'),
    path('admin-ui/api/counselors/', api_counselors, name='api_counselors'),
    path('admin-ui/api/cases/<str:case_id>/assign/', api_assign_case, name='api_assign_case'),
    
    # Django admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('bot.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

