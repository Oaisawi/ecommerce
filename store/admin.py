from django.contrib import admin
from django.utils.html import format_html

from .models import Address, CartItem, Category, Coupon, Order, OrderItem, Payment, Product, Review, StockAdjustment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "product_author", "unit_price", "quantity", "line_total")
    can_delete = False

    def line_total(self, obj):
        return f"${obj.line_total:,.2f}"
    line_total.short_description = "Line Total"


class StockAdjustmentInline(admin.TabularInline):
    model = StockAdjustment
    extra = 0
    readonly_fields = ("created_by", "created_at")
    autocomplete_fields = ["product"]


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ("user", "rating", "comment", "created_at")
    can_delete = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "category", "price", "sale_price", "stock", "stock_status_display", "is_active", "is_featured", "updated_at")
    list_filter = ("is_active", "is_featured", "category", "format")
    search_fields = ("name", "author", "isbn", "description")
    list_editable = ("price", "sale_price", "stock", "is_active", "is_featured")
    readonly_fields = ("slug", "created_at", "updated_at", "rating_avg", "rating_count")
    prepopulated_fields = {}
    inlines = [ReviewInline, StockAdjustmentInline]

    def stock_status_display(self, obj):
        status = obj.stock_status
        if status == "out_of_stock":
            color = "red"
        elif status == "low_stock":
            color = "orange"
        else:
            color = "green"
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, status.replace("_", " ").title())
    stock_status_display.short_description = "Stock Status"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
    readonly_fields = ("created_at",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "amount_off", "new_users_only", "used_count", "max_uses", "is_active", "expires_at")
    list_filter = ("is_active", "new_users_only")
    search_fields = ("code",)
    list_editable = ("is_active",)
    readonly_fields = ("used_count", "created_at")


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity_change", "reason", "created_by", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("product__name", "note")
    autocomplete_fields = ["product"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "updated_at")
    search_fields = ("user__username", "product__name")
    autocomplete_fields = ["user", "product"]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "full_name", "city", "country", "is_default")
    list_filter = ("type", "country")
    search_fields = ("user__username", "full_name", "city")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "status", "payment_status_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "shipping_address")
    inlines = [OrderItemInline]
    readonly_fields = ("subtotal", "discount_amount", "coupon", "created_at", "updated_at")
    list_editable = ("status",)

    def payment_status_display(self, obj):
        try:
            status = obj.payment.status
            colors = {"paid": "green", "pending": "orange", "failed": "red", "refunded": "purple"}
            return format_html(
                '<span style="color:{}; font-weight:bold;">{}</span>',
                colors.get(status, "gray"),
                obj.payment.get_status_display(),
            )
        except Payment.DoesNotExist:
            return format_html('<span style="color:gray;">No payment</span>')
    payment_status_display.short_description = "Payment"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("txn_id", "order", "method", "status", "amount", "card_last4", "created_at")
    list_filter = ("method", "status", "created_at")
    search_fields = ("txn_id", "order__user__username", "card_last4")
    readonly_fields = ("txn_id", "order", "method", "amount", "card_brand", "card_last4", "wallet_email", "created_at")
    actions = ["mark_refunded"]

    def mark_refunded(self, request, queryset):
        updated = queryset.exclude(status=Payment.Status.REFUNDED).update(status=Payment.Status.REFUNDED)
        self.message_user(request, f"{updated} payment(s) marked as refunded (mock — no money moved).")
    mark_refunded.short_description = "Mark selected payments as refunded (mock)"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "product_author", "unit_price", "quantity")
    search_fields = ("product_name", "order__user__username")
