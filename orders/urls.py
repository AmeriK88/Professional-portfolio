from django.urls import path
from . import views

app_name = "orders"
urlpatterns = [
    path("checkout/<slug:slug>/", views.checkout_service, name="checkout_service"),
]
