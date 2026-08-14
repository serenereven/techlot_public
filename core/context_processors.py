from django.core.cache import cache
from core.models import Contact, BasicPage, ContactType
# from .forms import PurchaseRequestForm

CACHE_KEY = "global_header_footer:v1"
CACHE_TTL = 60 * 10  # 10 минут


def global_header_footer(request):
    data = cache.get(CACHE_KEY)
    if data:
        return data

    qs = Contact.published.order_by("sort_order")
    social_types = [ContactType.TELEGRAM, ContactType.VK, ContactType.WHATSAPP]

    socials = list(qs.filter(contact_type__in=social_types))
    contacts = list(qs.exclude(contact_type__in=social_types))
    conact_phone = next((c for c in contacts if c.contact_type == ContactType.PHONE), None)

    data = {
        "socials": socials,
        "contacts": contacts,
        "conact_phone": conact_phone,
        "pages_menu": list(BasicPage.published.alive().filter(is_navbar=True)),
        # "purchase_form": PurchaseRequestForm()
    }
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data
