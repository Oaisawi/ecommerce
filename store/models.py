import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    """Catalog helpers — only books with an uploaded cover or external image URL."""

    def with_listing_image(self):
        return self.filter(
            (~Q(image="")) | (Q(image_url__isnull=False) & ~Q(image_url="")),
        )


class Product(models.Model):
    class Format(models.TextChoices):
        PAPERBACK = "paperback", "Paperback"
        HARDCOVER = "hardcover", "Hardcover"
        EBOOK = "ebook", "eBook"
        AUDIOBOOK = "audiobook", "Audiobook"

    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    author = models.CharField(max_length=200, default="Unknown Author")
    isbn = models.CharField(max_length=20, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    published_date = models.DateField(null=True, blank=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default="English")
    format = models.CharField(max_length=20, choices=Format.choices, default=Format.PAPERBACK)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Set a sale price lower than the regular price to mark as on sale.",
    )
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True)
    image_url = models.URLField(blank=True, help_text="Fallback if no image uploaded")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "book"
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("product_detail", kwargs={"slug": self.slug})

    @property
    def effective_price(self):
        if self.sale_price and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def is_on_sale(self):
        return bool(self.sale_price and self.sale_price < self.price)

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return (self.image_url or "").strip()

    @property
    def stock_status(self):
        if self.stock == 0:
            return "out_of_stock"
        if self.stock <= 5:
            return "low_stock"
        return "in_stock"

    @property
    def rating_stars(self):
        """Returns a list of 5 values: 'full', 'half', or 'empty' for star rendering."""
        stars = []
        avg = float(self.rating_avg)
        for i in range(1, 6):
            if avg >= i:
                stars.append("full")
            elif avg >= i - 0.5:
                stars.append("half")
            else:
                stars.append("empty")
        return stars


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_review_per_user_product"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} → {self.product.name} ({self.rating}★)"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    percent_off = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MaxValueValidator(100)],
        help_text="Percentage discount (1–100). Use either percent_off or amount_off, not both.",
    )
    amount_off = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Fixed amount discount. Use either percent_off or amount_off, not both.",
    )
    max_uses = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    new_users_only = models.BooleanField(
        default=False,
        help_text="If checked, only customers who have never placed an order may use this code.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.percent_off:
            return f"{self.code} ({self.percent_off}% off)"
        return f"{self.code} (${self.amount_off} off)"

    def calculate_discount(self, subtotal):
        if self.percent_off:
            return (subtotal * self.percent_off / 100).quantize(Decimal("0.01"))
        if self.amount_off:
            return min(self.amount_off, subtotal)
        return Decimal("0.00")

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def user_may_redeem(self, user):
        """First-order / new-user coupons: only if this user has never placed an order."""
        if not self.new_users_only:
            return True
        if not getattr(user, "is_authenticated", False):
            return False
        from django.apps import apps

        OrderModel = apps.get_model("store", "Order")
        return not OrderModel.objects.filter(user=user).exists()


class StockAdjustment(models.Model):
    class Reason(models.TextChoices):
        SALE = "sale", "Sale"
        RESTOCK = "restock", "Restock"
        RETURN = "return", "Return"
        DAMAGE = "damage", "Damage"
        MANUAL = "manual", "Manual Adjustment"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_adjustments")
    quantity_change = models.IntegerField(help_text="Positive for restock, negative for reduction")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name}: {self.quantity_change:+d} ({self.reason})"


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_cart_item_per_user_product"),
        ]
        ordering = ["product__name"]

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def line_total(self):
        return self.product.effective_price * self.quantity


class Address(models.Model):
    class Type(models.TextChoices):
        SHIPPING = "shipping", "Shipping"
        BILLING = "billing", "Billing"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.SHIPPING)
    full_name = models.CharField(max_length=200)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="United States")
    phone = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, type=self.type).update(is_default=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.user.username}"

    @property
    def can_cancel(self):
        return self.status in [self.Status.PENDING, self.Status.PROCESSING]

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    product_author = models.CharField(max_length=200, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["product_name"]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


def _mock_txn_id():
    return "MOCK-" + uuid.uuid4().hex[:10].upper()


class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = "card", "Credit / Debit Card"
        APPLE_PAY = "apple_pay", "Apple Pay"
        GOOGLE_PAY = "google_pay", "Google Pay"
        PAYPAL = "paypal", "PayPal"
        COD = "cod", "Cash on Delivery"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    txn_id = models.CharField(max_length=50, default=_mock_txn_id)
    card_brand = models.CharField(max_length=10, blank=True, help_text="VISA / MC / AMEX / DISCOVER")
    card_last4 = models.CharField(max_length=4, blank=True)
    wallet_email = models.CharField(max_length=200, blank=True, help_text="PayPal / Google Pay mock email")
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.txn_id} — {self.get_status_display()} ({self.get_method_display()})"

    @property
    def masked_card(self):
        if self.card_last4:
            return f"•••• •••• •••• {self.card_last4}"
        return ""
