from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("django_sitemap"))

    lines = [
        "User-Agent: *",
        "Disallow:",
        f"Sitemap: {sitemap_url}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def error_page(request, exception=None):
    """
    Единый обработчик ошибок 400/403/404/500.
    """
    status_code = 500

    if exception is not None:
        name = exception.__class__.__name__
        if "NotFound" in name:
            status_code = 404
        elif "PermissionDenied" in name:
            status_code = 403
        elif "SuspiciousOperation" in name:
            status_code = 400

    context = {
        "status_code": status_code,
        "path": request.path,
    }
    return render(request, "error.html", context=context, status=status_code)
