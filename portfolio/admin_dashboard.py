from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.urls import reverse
from blog.models import Post
from projects.models import Project
from services.models import Service



def dashboard_callback(request, context):
    key = "admin_kpis:v3" 
    data = cache.get(key)
    if data is None:
        User = get_user_model()
        app_label = User._meta.app_label    
        model_name = User._meta.model_name  

        data = {
            "kpi_posts": Post.objects.count(),
            "kpi_projects": Project.objects.count(),
            "kpi_services": Service.objects.count(),
            "kpi_services_active": Service.objects.filter(is_active=True).count(),
            "kpi_services_inactive": Service.objects.filter(is_active=False).count(),
            "kpi_services_sum_price": Service.objects.aggregate(total=Sum("price"))["total"] or 0,
            "kpi_users": User.objects.count(),

            # URLs del admin (dinámicas, válidas con custom user):
            "admin_user_list_url":  reverse(f"admin:{app_label}_{model_name}_changelist"),
            "admin_user_change_url": reverse(f"admin:{app_label}_{model_name}_change",
                                             args=[request.user.pk]),
        }
        cache.set(key, data, 60)

    # Copia y filtra métricas sensibles
    data_out = dict(data)
    if not request.user.is_superuser:
        data_out.pop("kpi_services_sum_price", None)

    # (permiso change sobre el modelo)
    User = get_user_model()
    perm_codename = f"{User._meta.app_label}.change_{User._meta.model_name}"
    data_out["can_edit_self"] = request.user.has_perm(perm_codename)

    context.update(data_out)
    return context
