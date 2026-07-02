from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def money(value, symbol=None):
    """Render a price with the store currency symbol, e.g. $29.99"""
    sym = symbol or getattr(settings, "STORE_CURRENCY_SYMBOL", "$")
    try:
        d = Decimal(str(value))
        return f"{sym}{d:,.2f}"
    except (InvalidOperation, TypeError):
        return f"{sym}0.00"


@register.filter
def stars_range(avg):
    """Return a list of tuples (index, kind) for star rendering where kind is full/half/empty."""
    result = []
    try:
        avg = float(avg)
    except (TypeError, ValueError):
        avg = 0.0
    for i in range(1, 6):
        if avg >= i:
            result.append("full")
        elif avg >= i - 0.5:
            result.append("half")
        else:
            result.append("empty")
    return result


@register.filter
def payment_method_icon(method):
    """Return a small inline SVG for the payment method."""
    _card = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>'
    _apple = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>'
    _gpay = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 11.3v1.9h3c-.2 1-1.1 2.8-3 2.8-1.8 0-3.3-1.5-3.3-3.3s1.5-3.3 3.3-3.3c1 0 1.7.4 2.1.8l1.3-1.3C14.5 7.8 13.3 7.2 12 7.2 9.1 7.2 6.8 9.5 6.8 12.4s2.3 5.2 5.2 5.2c3 0 5-2.1 5-5.1 0-.3 0-.6-.1-.8H12z"/></svg>'
    _paypal = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7.144 19.532l1.049-5.751c.11-.607.691-1.032 1.304-.95 2.329.308 3.89-.005 4.744-1.12.853-1.114.853-2.847.012-4.64C13.433 5.372 11.833 5 10.164 5H5.51a.994.994 0 00-.984.838L3 17.502a.573.573 0 00.565.667h2.58l.999-3.637z"/><path d="M18.76 8.516c.095 3.22-1.955 5.484-5.16 5.484H12l-1 5.333h2.191a.855.855 0 00.845-.715l1.028-5.558c.078-.428.449-.742.885-.742 2.145 0 3.664-.888 4.12-2.738.215-.871.054-1.484-.309-2.064z"/></svg>'
    _cod = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>'
    _default = '<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" d="M12 8v4m0 4h.01"/></svg>'
    icons = {
        "card": _card,
        "apple_pay": _apple,
        "google_pay": _gpay,
        "paypal": _paypal,
        "cod": _cod,
    }
    return mark_safe(icons.get(method, _default))


@register.filter
def stock_label(product):
    """Return a human-readable stock label (never exposes raw counts to customers)."""
    status = product.stock_status
    if status == "out_of_stock":
        return "Out of Stock"
    if status == "low_stock":
        return f"Only {product.stock} left"
    return "In Stock"


_STAR_SVG = (
    '<svg class="w-4 h-4 inline-block {color}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">'
    '<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 '
    "1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 "
    "1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 "
    '1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>'
)

_STAR_HALF_SVG = (
    '<svg class="w-4 h-4 inline-block text-yellow-300" viewBox="0 0 20 20" aria-hidden="true">'
    '<defs><linearGradient id="half"><stop offset="50%" stop-color="currentColor"/>'
    '<stop offset="50%" stop-color="#d1d5db"/></linearGradient></defs>'
    '<path fill="url(#half)" d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 '
    "1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 "
    "1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 "
    '1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>'
)


@register.simple_tag
def rating_stars_html(avg, count=0):
    """Render star SVG icons as HTML string."""
    try:
        avg = float(avg)
    except (TypeError, ValueError):
        avg = 0.0

    stars_html = ""
    for i in range(1, 6):
        if avg >= i:
            stars_html += _STAR_SVG.format(color="text-yellow-400")
        elif avg >= i - 0.5:
            stars_html += _STAR_HALF_SVG
        else:
            stars_html += _STAR_SVG.format(color="text-gray-300")

    if count:
        stars_html += f'<span class="text-gray-500 text-xs ml-1">({count})</span>'
    return mark_safe(stars_html)
