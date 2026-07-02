import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import (
    AddressForm,
    CartAddForm,
    CartUpdateForm,
    CategoryForm,
    CheckoutForm,
    OrderStatusForm,
    ProductForm,
    RegisterForm,
    ReviewForm,
    StockAdjustmentForm,
)
from .models import Address, CartItem, Category, Coupon, Order, OrderItem, Payment, Product, Review, StockAdjustment
from .payments import process_payment

logger = logging.getLogger("store")


def _discount_from_coupon_code(user, coupon_code, subtotal):
    """Return (discount_decimal, coupon_or_none). Always recalculate server-side — never trust session amounts."""
    code = (coupon_code or "").strip()
    if not code:
        return Decimal("0.00"), None
    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return Decimal("0.00"), None
    if not coupon.is_valid() or not coupon.user_may_redeem(user):
        return Decimal("0.00"), None
    return coupon.calculate_discount(subtotal), coupon


# ─────────────────────────── Public ────────────────────────────

def home(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    products = (
        Product.objects.filter(is_active=True)
        .with_listing_image()
        .select_related("category")
    )

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(author__icontains=query) | Q(description__icontains=query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    sort_options = {
        "name": "name",
        "price_low": "price",
        "price_high": "-price",
        "newest": "-created_at",
        "rating": "-rating_avg",
    }
    products = products.order_by(sort_options.get(sort, "-created_at"))

    cover_q = (
        Q(products__is_active=True)
        & ((~Q(products__image="")) | (Q(products__image_url__isnull=False) & ~Q(products__image_url="")))
    )
    categories = (
        Category.objects.annotate(product_count=Count("products", filter=cover_q))
        .filter(product_count__gt=0)
    )
    featured = (
        Product.objects.filter(is_active=True, is_featured=True)
        .with_listing_image()
        .select_related("category")[:6]
    )
    new_releases = Product.objects.filter(is_active=True).with_listing_image().order_by("-created_at")[:8]
    on_sale = (
        Product.objects.filter(is_active=True, sale_price__isnull=False)
        .exclude(sale_price=0)
        .with_listing_image()[:8]
    )

    context = {
        "products": products,
        "categories": categories,
        "featured": featured,
        "new_releases": new_releases,
        "on_sale": on_sale,
        "query": query,
        "current_category": category_slug,
        "current_sort": sort,
        "product_count": products.count(),
        "is_search": bool(query or category_slug),
    }
    return render(request, "store/home.html", context)


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Epic AI Reads! Your account has been created.")
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).with_listing_image(),
        slug=slug,
    )
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .with_listing_image()
        .exclude(pk=product.pk)[:4]
    )
    # Keep an unsliced queryset for filtering, then slice for display
    reviews_qs = product.reviews.select_related("user").order_by("-created_at")

    user_review = None
    user_has_bought = False
    review_form = None

    if request.user.is_authenticated:
        user_review = reviews_qs.filter(user=request.user).first()
        user_has_bought = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status__in=[Order.Status.COMPLETED, Order.Status.SHIPPED],
        ).exists()

        if user_has_bought and not user_review:
            if request.method == "POST" and "submit_review" in request.POST:
                review_form = ReviewForm(request.POST)
                if review_form.is_valid():
                    rev = review_form.save(commit=False)
                    rev.product = product
                    rev.user = request.user
                    rev.save()
                    # Update rating aggregates
                    all_ratings = product.reviews.values_list("rating", flat=True)
                    product.rating_count = len(all_ratings)
                    product.rating_avg = sum(all_ratings) / product.rating_count if product.rating_count else 0
                    product.save(update_fields=["rating_avg", "rating_count"])
                    messages.success(request, "Thank you for your review!")
                    return redirect("product_detail", slug=product.slug)
            else:
                review_form = ReviewForm()

    cart_form = CartAddForm(initial={"quantity": 1})

    context = {
        "product": product,
        "related_products": related,
        "reviews": reviews_qs[:20],
        "user_review": user_review,
        "user_has_bought": user_has_bought,
        "review_form": review_form,
        "cart_form": cart_form,
    }
    return render(request, "store/product_detail.html", context)


# ─────────────────────────── Cart ────────────────────────────

@login_required
def add_to_cart(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).with_listing_image(),
        slug=slug,
    )

    if request.method != "POST":
        return redirect("product_detail", slug=product.slug)

    form = CartAddForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid quantity.")
        return redirect("product_detail", slug=product.slug)

    quantity = form.cleaned_data["quantity"]
    if quantity > product.stock:
        messages.error(request, f"Sorry, only {product.stock} copies available.")
        return redirect("product_detail", slug=product.slug)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        new_qty = cart_item.quantity + quantity
        if new_qty > product.stock:
            messages.error(request, f"You already have {cart_item.quantity} in cart. Max available: {product.stock}.")
            return redirect("cart")
        cart_item.quantity = new_qty
        cart_item.save(update_fields=["quantity", "updated_at"])

    messages.success(request, f"Added {quantity} × {product.name} to your cart.")
    return redirect("cart")


@login_required
def cart(request):
    items = CartItem.objects.select_related("product").filter(user=request.user)
    subtotal = sum((item.line_total for item in items), Decimal("0.00"))
    item_count = sum(item.quantity for item in items)
    return render(request, "store/cart.html", {"items": items, "subtotal": subtotal, "item_count": item_count})


@login_required
def update_cart_item(request, pk):
    cart_item = get_object_or_404(CartItem.objects.select_related("product"), pk=pk, user=request.user)
    if request.method == "POST":
        form = CartUpdateForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            if quantity > cart_item.product.stock:
                messages.error(request, f"Only {cart_item.product.stock} copies available.")
            else:
                cart_item.quantity = quantity
                cart_item.save(update_fields=["quantity", "updated_at"])
    return redirect("cart")


@login_required
def remove_cart_item(request, pk):
    cart_item = get_object_or_404(CartItem, pk=pk, user=request.user)
    if request.method == "POST":
        name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f"Removed {name} from your cart.")
    return redirect("cart")


# ─────────────────────────── Checkout ────────────────────────────

@login_required
def checkout(request):
    items = CartItem.objects.select_related("product").filter(user=request.user)
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    subtotal = sum((item.line_total for item in items), Decimal("0.00"))

    if request.method == "POST":
        form = CheckoutForm(request.user, request.POST)
        if form.is_valid():
            coupon_code = form.cleaned_data.get("coupon_code", "").strip()

            request.session["checkout_data"] = {
                "shipping_address_id": form.cleaned_data["shipping_address"].pk,
                "billing_address_id": form.cleaned_data["billing_address"].pk if form.cleaned_data["billing_address"] else None,
                "coupon_code": coupon_code,
                "notes": form.cleaned_data.get("notes", ""),
            }
            return redirect("payment")
    else:
        form = CheckoutForm(request.user)

    return render(request, "store/checkout.html", {"form": form, "items": items, "subtotal": subtotal})


@login_required
def payment(request):
    checkout_data = request.session.get("checkout_data")
    if not checkout_data:
        messages.error(request, "Please start checkout from your cart.")
        return redirect("cart")

    items = CartItem.objects.select_related("product").filter(user=request.user)
    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    subtotal = sum((item.line_total for item in items), Decimal("0.00"))
    discount, _active_coupon = _discount_from_coupon_code(
        request.user, checkout_data.get("coupon_code", ""), subtotal
    )
    total = subtotal - discount

    shipping = get_object_or_404(Address, pk=checkout_data["shipping_address_id"], user=request.user)
    billing_id = checkout_data.get("billing_address_id")
    billing = get_object_or_404(Address, pk=billing_id, user=request.user) if billing_id else None

    error = None

    if request.method == "POST":
        method = request.POST.get("payment_method", "")

        if method == Payment.Method.CARD:
            result = process_payment(
                method=method,
                amount=total,
                card={
                    "number": request.POST.get("card_number", ""),
                    "exp": request.POST.get("card_exp", ""),
                    "cvc": request.POST.get("card_cvc", ""),
                    "name": request.POST.get("card_name", ""),
                },
            )
        elif method in (Payment.Method.APPLE_PAY, Payment.Method.GOOGLE_PAY, Payment.Method.PAYPAL):
            result = process_payment(
                method=method,
                amount=total,
                wallet_email=request.POST.get("wallet_email", ""),
            )
        elif method == Payment.Method.COD:
            result = process_payment(method=method, amount=total)
        else:
            messages.error(request, "Please select a payment method.")
            result = None

        if result and result.succeeded:
            coupon = None
            coupon_code = checkout_data.get("coupon_code", "")
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code__iexact=coupon_code)
                    coupon.used_count += 1
                    coupon.save(update_fields=["used_count"])
                except Coupon.DoesNotExist:
                    pass

            with transaction.atomic():
                cart_items = list(items)
                locked_products = {
                    p.pk: p
                    for p in Product.objects.select_for_update().filter(
                        pk__in=[i.product_id for i in cart_items]
                    )
                }

                for item in cart_items:
                    product = locked_products[item.product_id]
                    if not product.is_active or item.quantity > product.stock:
                        messages.error(request, f'"{product.name}" is no longer available in the requested quantity.')
                        return redirect("cart")

                order = Order.objects.create(
                    user=request.user,
                    subtotal=subtotal,
                    discount_amount=discount,
                    total_price=total,
                    status=Order.Status.PENDING,
                    shipping_address=str(shipping),
                    billing_address=str(billing) if billing else str(shipping),
                    coupon=coupon,
                    notes=checkout_data.get("notes", ""),
                )

                for item in cart_items:
                    product = locked_products[item.product_id]
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_author=product.author,
                        unit_price=product.effective_price,
                        quantity=item.quantity,
                    )
                    product.stock -= item.quantity
                    product.save(update_fields=["stock", "updated_at"])
                    StockAdjustment.objects.create(
                        product=product,
                        quantity_change=-item.quantity,
                        reason=StockAdjustment.Reason.SALE,
                        note=f"Order #{order.pk}",
                        created_by=request.user,
                    )

                Payment.objects.create(
                    order=order,
                    method=result.method,
                    status=Payment.Status.PAID if method != Payment.Method.COD else Payment.Status.PENDING,
                    amount=total,
                    card_brand=result.card_brand,
                    card_last4=result.card_last4,
                    wallet_email=result.wallet_email,
                )

                CartItem.objects.filter(pk__in=[i.pk for i in cart_items]).delete()
                del request.session["checkout_data"]

            # Send confirmation email (best-effort)
            try:
                _send_order_email(order)
            except Exception:
                logger.warning("Failed to send order confirmation email for order #%s", order.pk)

            messages.success(request, f"Order #{order.pk} placed successfully!")
            return redirect("order_confirmation", pk=order.pk)

        elif result and not result.succeeded:
            error = result.failure_reason

    context = {
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "shipping": shipping,
        "billing": billing,
        "error": error,
    }
    return render(request, "store/payment.html", context)


def _send_order_email(order):
    subject = f"Order #{order.pk} Confirmed — Epic AI Reads"
    html_body = render_to_string("emails/order_confirmation.html", {"order": order})
    text_body = render_to_string("emails/order_confirmation.txt", {"order": order})
    send_mail(
        subject,
        text_body,
        None,
        [order.user.email],
        html_message=html_body,
        fail_silently=False,
    )


@login_required
def order_confirmation(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)
    payment_obj = getattr(order, "payment", None)
    return render(request, "store/order_confirmation.html", {"order": order, "payment": payment_obj})


@login_required
def order_history(request):
    orders = Order.objects.prefetch_related("items").filter(user=request.user)
    return render(request, "store/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)
    payment_obj = getattr(order, "payment", None)
    return render(request, "store/order_detail.html", {"order": order, "payment": payment_obj})


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == "POST":
        if not order.can_cancel:
            messages.error(request, "This order cannot be cancelled.")
            return redirect("order_detail", pk=order.pk)

        with transaction.atomic():
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

            for item in order.items.select_related("product"):
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save(update_fields=["stock", "updated_at"])
                    StockAdjustment.objects.create(
                        product=item.product,
                        quantity_change=item.quantity,
                        reason=StockAdjustment.Reason.RETURN,
                        note=f"Cancelled Order #{order.pk}",
                        created_by=request.user,
                    )

        messages.success(request, f"Order #{order.pk} has been cancelled.")
    return redirect("order_history")


# ─────────────────────────── Profile / Address ────────────────────────────

@login_required
def profile(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)[:5]
    return render(request, "store/profile.html", {"addresses": addresses, "recent_orders": orders})


@login_required
def address_create(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address added.")
            return redirect("profile")
    else:
        form = AddressForm()
    return render(request, "store/address_form.html", {"form": form, "title": "Add Address"})


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated.")
            return redirect("profile")
    else:
        form = AddressForm(instance=address)
    return render(request, "store/address_form.html", {"form": form, "title": "Edit Address"})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.delete()
        messages.success(request, "Address removed.")
    return redirect("profile")


# ─────────────────────────── Staff / Dashboard ────────────────────────────

@staff_member_required
def dashboard(request):
    context = {
        "product_count": Product.objects.count(),
        "active_product_count": Product.objects.filter(is_active=True).count(),
        "low_stock_products": Product.objects.filter(is_active=True, stock__lte=5).order_by("stock", "name")[:10],
        "out_of_stock_count": Product.objects.filter(is_active=True, stock=0).count(),
        "order_count": Order.objects.count(),
        "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
        "total_revenue": Order.objects.filter(status=Order.Status.COMPLETED).aggregate(
            total=Sum("total_price")
        )["total"] or Decimal("0.00"),
        "latest_orders": Order.objects.select_related("user").prefetch_related("items")[:10],
        "recent_adjustments": StockAdjustment.objects.select_related("product", "created_by")[:10],
    }
    return render(request, "store/dashboard.html", context)


@staff_member_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            if product.stock > 0:
                StockAdjustment.objects.create(
                    product=product,
                    quantity_change=product.stock,
                    reason=StockAdjustment.Reason.RESTOCK,
                    note="Initial stock",
                    created_by=request.user,
                )
            messages.success(request, f"'{product.name}' created.")
            return redirect("dashboard")
    else:
        form = ProductForm()
    return render(request, "store/product_form.html", {"form": form, "title": "Add Book"})


@staff_member_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{product.name}' updated.")
            return redirect("dashboard")
    else:
        form = ProductForm(instance=product)
    return render(request, "store/product_form.html", {"form": form, "title": "Edit Book", "product": product})


@staff_member_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"'{product.name}' has been deactivated.")
        return redirect("dashboard")
    return render(request, "store/product_confirm_delete.html", {"product": product})


@staff_member_required
def stock_adjust(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment = form.save(commit=False)
            adjustment.product = product
            adjustment.created_by = request.user
            adjustment.save()
            product.stock = max(0, product.stock + adjustment.quantity_change)
            product.save(update_fields=["stock", "updated_at"])
            messages.success(request, f"Stock updated. New stock: {product.stock}")
            return redirect("dashboard")
    else:
        form = StockAdjustmentForm()
    return render(request, "store/stock_adjust.html", {"form": form, "product": product})


@staff_member_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    return render(request, "store/category_list.html", {"categories": categories})


@staff_member_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "store/category_form.html", {"form": form, "title": "Add Category"})


@staff_member_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "store/category_form.html", {"form": form, "title": "Edit Category", "category": category})


@staff_member_required
def order_management(request):
    status_filter = request.GET.get("status", "")
    orders = Order.objects.select_related("user").prefetch_related("items")
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, "store/order_management.html", {"orders": orders, "status_filter": status_filter})


@staff_member_required
def order_manage_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.status
            form.save()
            if old_status != order.status:
                messages.success(request, f"Status updated: {old_status} → {order.status}.")
            return redirect("order_management")
    else:
        form = OrderStatusForm(instance=order)
    return render(request, "store/order_manage_detail.html", {"order": order, "form": form})
