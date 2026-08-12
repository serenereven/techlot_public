from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def qs_without_page(context):
    request = context["request"]
    q = request.GET.copy()
    q.pop("page", None)
    s = q.urlencode()
    return ("&" + s) if s else ""