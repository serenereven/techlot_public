from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from core.models import Vehicle


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return ["core:index", "core:catalog", "core:about_page"]

    def location(self, item):
        return reverse(item)


class VehicleSitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Vehicle.published.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("core:vehicle_detail", kwargs={"slug": obj.slug})


sitemaps = {
    "static": StaticViewSitemap,
    "vehicles": VehicleSitemap,
}