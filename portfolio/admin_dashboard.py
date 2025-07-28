def dashboard_callback(request, context):
    from blog.models import Post
    from projects.models import Project
    from services.models import Service

    context.update({
        "kpi_posts": Post.objects.count(),
        "kpi_projects": Project.objects.count(),
        "kpi_services": Service.objects.count(),
    })
    return context
