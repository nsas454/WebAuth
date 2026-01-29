from django.urls import path
from .views import (
    RegisterOptionsView,
    RegisterVerifyView,
    LoginOptionsView,
    LoginVerifyView,
)

urlpatterns = [
    path("register/options", RegisterOptionsView.as_view()),
    path("register/verify", RegisterVerifyView.as_view()),
    path("login/options", LoginOptionsView.as_view()),
    path("login/verify", LoginVerifyView.as_view()),
]
