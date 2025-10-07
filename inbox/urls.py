from django.urls import path
from . import views

app_name = "inbox"

urlpatterns = [
    path("", views.thread_list, name="thread_list"),
    path("<int:thread_id>/", views.thread_detail, name="thread_detail"),
]
