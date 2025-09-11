from django.shortcuts import render
from .models import Project
from blog.models import Post   
                                         
def home(request):
    latest_projects = Project.objects.order_by('-created_at')[:3]
    latest_posts    = Post.objects.order_by('-created_at')[:3]

    stats = [           
        (+34, 'Repos'),
        (+8, 'Clientes'),
        (+5,  'Años de experiencia'),
    ]

    context = {
        'latest_projects': latest_projects,
        'latest_posts': latest_posts,
        'stats': stats,
    }
    return render(request, 'home.html', context)

def project_list(request):
    projects = Project.objects.all()
    return render(request, 'projects/project_list.html', {'projects': projects})
