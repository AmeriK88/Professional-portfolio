from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Service

def service_list(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'services/service_list.html', {'services': services})

@ensure_csrf_cookie
def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    # FAQs llegarán por related_name "faqs"
    return render(request, "services/service_detail.html", {"service": service})

def payment_success(request):
    pid = request.GET.get("pid")
    return render(request, "services/payment_success.html", {"payment_id": pid})
