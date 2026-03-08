from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # login/logout
    path("", include("social_django.urls", namespace="social")),
    path("", include("tracker.urls")),
]
