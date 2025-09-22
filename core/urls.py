from django.urls import path
from . import views

app_name = "core"  

urlpatterns = [
    path("", views.home, name="home"),
    path("legal/privacidad/", views.legal_privacidad, name="legal_privacidad"),
    path("legal/cookies/", views.cookies_policy, name="legal_cookies"),
]
