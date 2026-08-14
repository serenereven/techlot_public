# from django.db.models import Q
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404
from django.core.paginator import Paginator
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.template.loader import render_to_string
from .filters import VehicleFilter, get_clean_queryset, get_available_vehicle_types
from .models import Vehicle, Brand, City, VehicleModel, VehicleType, BasicPage, StockStatus
from .forms import PurchaseRequestForm

from core.services.bitrix.lead import BitrixLeadService
from core.services.bitrix.exceptions import BitrixError

from .export_utils import (
    get_cached_export_data,
    get_export_filename,
    # clear_export_cache
)


def public_vehicles_queryset():
    return Vehicle.published.alive().order_by("-to_homepage", "-created_at")


def default_catalog_queryset():
    """
    Сортировка по умолчанию: по категории, затем по дате.
    Применяется пока пользователь не выбрал свою сортировку.
    """
    return Vehicle.published.alive().order_by("vehicle_type__name", "-to_homepage", "-created_at")


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vehicles_queryset = public_vehicles_queryset()

        ctx["latest_vehicles"] = public_vehicles_queryset()[:8]
        ctx["latest_vehicles_count"] = vehicles_queryset.count()

        ctx["all_brands"] = get_clean_queryset(Brand).order_by("name")
        ctx["all_models"] = get_clean_queryset(VehicleModel).select_related("brand").order_by("name")

        ctx["vehicle_types"] = VehicleType.objects.all().order_by("order")
        ctx["selected_brand_ids"] = self.request.GET.getlist("brand")
        ctx["selected_model_ids"] = self.request.GET.getlist("model")
        ctx["filter"] = VehicleFilter(self.request.GET or None, queryset=public_vehicles_queryset())
        return ctx


class VehicleListView(ListView):
    template_name = "core/vehicle_list.html"
    context_object_name = "vehicles"
    paginate_by = 12

    def get_queryset(self):
        sort_param = self.request.GET.get("sort")

        if not sort_param:
            base_qs = default_catalog_queryset().order_by("vehicle_type__order", "-created_at")
        else:
            base_qs = public_vehicles_queryset()

        base_qs = base_qs.select_related("brand", "model", "city", "vehicle_type")

        self.filterset = VehicleFilter(self.request.GET, queryset=base_qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        ctx["filter_form"] = self.filterset.form
        ctx["vehicle_types"] = get_available_vehicle_types()
        ctx["stock_statuses"] = StockStatus.choices

        ctx["all_brands"] = get_clean_queryset(Brand).order_by("name")
        ctx["all_models"] = get_clean_queryset(VehicleModel).select_related("brand").order_by("name")

        city_id = self.request.GET.get("city")
        ctx["selected_vehicle_types"] = self.request.GET.getlist("vehicle_type")
        ctx["selected_brand_ids"] = self.request.GET.getlist("brand")
        ctx["selected_model_ids"] = self.request.GET.getlist("model")
        ctx["selected_stock_statuses"] = self.request.GET.getlist("stock_status")
        ctx["selected_city"] = City.objects.filter(id=city_id).first() if city_id else None
        return ctx


@method_decorator(cache_page(60 * 5), name="dispatch")
class VehicleAjaxListView(View):
    paginate_by = 12

    def get(self, request, *args, **kwargs):
        lv = VehicleListView()
        lv.request = request
        qs = lv.get_queryset()

        paginator = Paginator(qs, self.paginate_by)
        page_number = int(request.GET.get("page") or 1)
        page_obj = paginator.get_page(page_number)

        context = {
            "vehicles": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "request": request,
        }

        items_html = render_to_string("core/partials/vehicle_grid.html", context, request=request)
        pagination_html = render_to_string("core/partials/vehicle_pagination.html", context, request=request)

        return JsonResponse(
            {
                "items_html": items_html,
                "pagination_html": pagination_html,
                "total": paginator.count,
                "has_more": page_obj.has_next(),  # для infinite scroll
                "next_page": page_number + 1 if page_obj.has_next() else None,
            }
        )


@require_GET
@cache_page(60 * 10)
def api_brands(request):
    q = (request.GET.get("q") or "").strip()
    qs = Brand.objects.order_by("name")
    if q:
        qs = qs.filter(name__icontains=q)
    return JsonResponse({"results": [{"id": str(b.id), "text": b.name} for b in qs[:20]]})


@require_GET
@cache_page(60 * 10)
def api_models(request):
    q = (request.GET.get("q") or "").strip()
    brand_id = request.GET.get("brand")
    qs = VehicleModel.objects.order_by("name")
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    if q:
        qs = qs.filter(name__icontains=q)
    return JsonResponse({"results": [{"id": str(m.id), "text": m.name} for m in qs[:20]]})


@require_GET
@cache_page(60 * 10)
def api_cities(request):
    q = (request.GET.get("q") or "").strip()
    qs = City.objects.order_by("name")
    if q:
        qs = qs.filter(name__icontains=q)
    return JsonResponse({"results": [{"id": str(c.id), "text": c.name} for c in qs[:20]]})


class VehicleDetailView(DetailView):
    template_name = "core/vehicle_detail.html"
    context_object_name = "vehicle"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return public_vehicles_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vehicle = self.object
        ctx["similar_vehicles"] = (
            public_vehicles_queryset()
            .filter(brand_id=vehicle.brand_id, vehicle_type=vehicle.vehicle_type)
            .exclude(pk=vehicle.pk)[:6]
        )
        return ctx


class BasicPageDetailView(DetailView):
    template_name = "core/basic_page.html"
    context_object_name = "page"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return BasicPage.published.alive()


class AboutPageDetailView(DetailView):
    template_name = "core/about_page.html"
    context_object_name = "page"

    def get_queryset(self):
        # Возвращаем queryset, отфильтрованный по slug 'about'
        return BasicPage.published.alive().filter(slug="about")

    def get_object(self, queryset=None):
        """
        Переопределяем get_object, так как у нас нет slug/pk в URL.
        Мы знаем, что объект должен быть один (или его нет).
        """
        if queryset is None:
            queryset = self.get_queryset()

        try:
            # Получаем первый объект из отфильтрованного queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist as e:
            raise Http404("Страница не найдена") from e

        return obj


@require_POST
@csrf_protect
def purchase_request_ajax(request):
    try:
        form = PurchaseRequestForm(request.POST)

        vehicle = None
        vehicle_id = request.POST.get("vehicle_id")
        vehicle_slug = request.POST.get("vehicle_slug")

        if vehicle_id:
            vehicle = Vehicle.published.alive().filter(pk=vehicle_id).first()
            if not vehicle:
                return JsonResponse({"ok": False, "errors": {"vehicle_id": ["Автомобиль не найден"]}}, status=400)
        elif vehicle_slug:
            vehicle = Vehicle.published.alive().filter(slug=vehicle_slug).first()
            if not vehicle:
                return JsonResponse({"ok": False, "errors": {"vehicle_slug": ["Автомобиль не найден"]}}, status=400)

        if not form.is_valid():
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)

        obj = form.save(commit=False)
        obj.vehicle = vehicle
        obj.source = "site"
        obj.save()

        service = BitrixLeadService()
        try:
            service.create_from_purchase_request(obj)
            obj.bitrix_sent = True
            obj.bitrix_error = ""
            obj.save(update_fields=["bitrix_sent", "bitrix_error"])
        except BitrixError as e:
            obj.bitrix_sent = False
            obj.bitrix_error = str(e)
            obj.save(update_fields=["bitrix_sent", "bitrix_error"])

        return JsonResponse({"ok": True, "message": "Спасибо, мы свяжемся с вами"})

    except Exception:
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"ok": False, "errors": {"__all__": ["Внутренняя ошибка сервера"]}},
            status=500,
        )


@require_GET
def export_vehicles_vin_excel(request):
    """Экспорт каталога с VIN. Кеш 1 час, rate-limit 5 мин на IP."""
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    rate_limit_key = f"vehicles_export_rate_limit_{client_ip}"

    if cache.get(rate_limit_key):
        return HttpResponseForbidden("Слишком частые запросы. Попробуйте снова через 5 минут.")

    cache.set(rate_limit_key, True, timeout=300)

    excel_data = get_cached_export_data(request)

    response = HttpResponse(
        excel_data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={get_export_filename()}"
    return response
