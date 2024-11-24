from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Página de inicio
    path('projects/', views.project_list, name='project_list'),
]
