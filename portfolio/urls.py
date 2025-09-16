from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as mediaserve

urlpatterns = [
    path('', include(('projects.urls', 'projects'), namespace='projects')),
    path('admin/', admin.site.urls),
    path('blog/', include('blog.urls')),
    path("services/", include(("services.urls", "services"), namespace="services")),
    path("pi/", include(("pi_payments.urls", "pi"), namespace="pi")),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Servir MEDIA en producción desde el volumen
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", mediaserve, {"document_root": settings.MEDIA_ROOT}),
    ]
