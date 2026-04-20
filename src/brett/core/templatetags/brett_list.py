from django import template
from django.utils.html import format_html
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def sort_header(context, key, label, default_dir="asc"):
    """Render a sortable table header link that preserves the current query.

    Toggles direction when the column is already active; otherwise starts in
    the provided default direction.
    """
    request = context["request"]
    current_sort = context.get("sort")
    current_dir = context.get("dir")

    if current_sort == key:
        next_dir = "desc" if current_dir == "asc" else "asc"
        indicator = "\u2193" if current_dir == "desc" else "\u2191"
        label_with_indicator = f"{label} {indicator}"
    else:
        next_dir = default_dir
        label_with_indicator = label

    params = request.GET.copy()
    params["sort"] = key
    params["dir"] = next_dir
    return format_html(
        '<a href="?{}">{}</a>', urlencode(params, doseq=True), label_with_indicator
    )
