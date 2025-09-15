from django.urls import path
from . import views

urlpatterns = [
    path("approve/",  views.pi_approve,  name="approve"),
    path("complete/", views.pi_complete, name="complete"),
    path("cancel/",   views.pi_cancel,   name="cancel"),
    path("webhook/",  views.pi_webhook,  name="webhook"),  
]
