from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), 
    path('projects/', views.project_list, name='project_list'),
]
