from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as mediaserve
from core.views import validation_key_view


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls", namespace="core")),
    path("blog/", include(("blog.urls", "blog"), namespace="blog")),
    path("projects/", include(("projects.urls", "projects"), namespace="projects")),
    path("services/", include(("services.urls", "services"), namespace="services")),
    path("pi/", include(("pi_payments.urls", "pi"), namespace="pi")),
    path("users/", include(("users.urls", "users"), namespace="users")),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
    path("validation-key.txt", validation_key_view, name="validation_key"),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", mediaserve, {"document_root": settings.MEDIA_ROOT}),
    ]
