from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/webauthn/", include("webauthn_api.urls")),
]
