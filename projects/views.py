from django.shortcuts import render
from django.core.cache import cache
from .models import Project
from blog.models import Post

def _order_by_first_available(qs, *candidates):
    """
    Ordena el queryset por el primer campo existente de la lista de candidatos.
    Ej: _order_by_first_available(qs, '-updated_at', '-created_at', '-id')
    """
    field_names = {f.name for f in qs.model._meta.fields}
    for f in candidates:
        if f.lstrip("-") in field_names:
            return qs.order_by(f)
    return qs

def home(request):
    # Últimos proyectos (created_at si existe, si no id)
    projects_qs = Project.objects.all()
    latest_projects = _order_by_first_available(projects_qs, "-created_at", "-id")[:3]

    # Últimos posts
    posts_qs = Post.objects.all()
    latest_posts = _order_by_first_available(posts_qs, "-created_at", "-id")[:3]

    # Servicios destacados (con tolerancia a esquema + opcional caché)
    featured_services = cache.get("home_featured_services")
    if featured_services is None:
        try:
            from services.models import Service  # import perezoso
            qs = Service.objects.all()
            if hasattr(Service, "is_active"):
                qs = qs.filter(is_active=True)
            qs = _order_by_first_available(qs, "-updated_at", "-created_at", "-id")
            featured_services = list(qs[:3])
        except Exception:
            featured_services = []
        # cache 1 minuto (ajusta a tu gusto o quítalo si no lo necesitas)
        cache.set("home_featured_services", featured_services, 60)

    # Stats como enteros (tu contador JS lo agradecerá)
    stats = [
        (35, "Repos"),
        (+10,  "Clientes"),
        (6,  "Años de experiencia"),
    ]

    context = {
        "latest_projects": latest_projects,
        "latest_posts": latest_posts,
        "featured_services": featured_services,
        "stats": stats,
    }
    return render(request, "home.html", context)


def project_list(request):
    projects = Project.objects.all()
    return render(request, "projects/project_list.html", {"projects": projects})
