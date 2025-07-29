from django.urls import path
from . import views
from .views import service_list, service_detail

app_name = "services" 

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path("<slug:slug>/", views.service_detail, name="detail"),
]
