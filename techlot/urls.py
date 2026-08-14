from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from common.views import robots_txt
from django.contrib.sitemaps.views import sitemap
from common.sitemaps import sitemaps


urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("", include(("core.urls", "core"), namespace="core")),
    # SEO
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django_sitemap"),
    path("sitemap", RedirectView.as_view(url="/sitemap.xml", permanent=True), name="sitemap_redirect"),
]

handler400 = "common.views.error_page"
handler403 = "common.views.error_page"
handler404 = "common.views.error_page"
handler500 = "common.views.error_page"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
