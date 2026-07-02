from django.apps import apps
from django.conf import settings


def cart_count(request):
    """Adds cart_count to every template context — one DB query per authenticated request."""
    count = 0
    if request.user.is_authenticated:
        count = request.user.cart_items.count()
    return {"cart_count": count}


def store_settings(request):
    """Exposes store-wide settings to templates."""
    return {
        "STORE_CURRENCY_SYMBOL": getattr(settings, "STORE_CURRENCY_SYMBOL", "$"),
        "STORE_CURRENCY": getattr(settings, "STORE_CURRENCY", "USD"),
    }


def new_user_coupon_promo(request):
    """First-order welcome coupon code + whether the current user may redeem it."""
    code = getattr(settings, "STORE_NEW_USER_COUPON_CODE", "") or ""
    pct = getattr(settings, "STORE_NEW_USER_COUPON_PERCENT", 15)
    eligible = False
    if code and getattr(request.user, "is_authenticated", False):
        Order = apps.get_model("store", "Order")
        eligible = not Order.objects.filter(user=request.user).exists()
    return {
        "new_user_coupon_code": code,
        "new_user_coupon_percent": pct,
        "new_user_coupon_eligible": eligible,
    }
