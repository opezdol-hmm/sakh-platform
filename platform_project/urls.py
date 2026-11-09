from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Superuser 'admin' created with password 'admin123'")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cases.urls')),
]