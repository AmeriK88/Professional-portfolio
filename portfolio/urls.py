from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('projects.urls')), 
    path('admin/', admin.site.urls),
    path('blog/', include('blog.urls')),  
    path("services/", include(("services.urls", "services"), namespace="services")),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
