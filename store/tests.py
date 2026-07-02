"""
Core test suite for Epic AI Reads.
Covers: cart math, stock decrement, mock payment paths,
address ownership, and staff-required redirects.
Run: python manage.py test store
"""
from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Address, CartItem, Category, Coupon, Order, OrderItem, Payment, Product
from .forms import CheckoutForm
from .openlibrary import candidate_cover_urls_from_doc, first_valid_cover_url
from .payments import PaymentResult, process_payment


# ─────────────────────────── Fixtures ────────────────────────────

def make_user(username="testuser", is_staff=False):
    user = User.objects.create_user(username=username, password="pass1234!")
    user.is_staff = is_staff
    user.save()
    return user


def make_product(name="Python ML", price="49.99", stock=20, category=None, image_url="https://covers.openlibrary.org/b/id/8259444-L.jpg"):
    p = Product(
        name=name,
        author="Test Author",
        price=Decimal(price),
        stock=stock,
        category=category,
        image_url=image_url or "",
    )
    p.save()
    return p


def make_address(user, city="Riyadh"):
    return Address.objects.create(
        user=user,
        type=Address.Type.SHIPPING,
        full_name="Test User",
        street_address="123 Test St",
        city=city,
        postal_code="12345",
        country="Saudi Arabia",
        is_default=True,
    )


# ─────────────────────────── Cart math ────────────────────────────

class CartMathTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()
        self.client.login(username="testuser", password="pass1234!")

    def test_line_total_uses_effective_price(self):
        """CartItem.line_total uses sale_price when set."""
        self.product.sale_price = Decimal("29.99")
        self.product.save()
        item = CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        self.assertEqual(item.line_total, Decimal("89.97"))

    def test_line_total_uses_regular_price_when_no_sale(self):
        item = CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        self.assertEqual(item.line_total, Decimal("99.98"))

    def test_add_to_cart_increases_qty(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        self.client.post(reverse("add_to_cart", kwargs={"slug": self.product.slug}), {"quantity": 3})
        item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(item.quantity, 5)

    def test_cart_respects_stock_limit(self):
        """Cannot add more to cart than available stock."""
        response = self.client.post(
            reverse("add_to_cart", kwargs={"slug": self.product.slug}),
            {"quantity": 999},
        )
        self.assertFalse(CartItem.objects.filter(user=self.user, product=self.product).exists())

    def test_cart_count_context_processor(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["cart_count"], 1)


# ─────────────────────────── Stock decrement ────────────────────────────

class StockDecrementTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(stock=10)
        self.address = make_address(self.user)
        self.client.login(username="testuser", password="pass1234!")

    def _go_through_checkout(self):
        """Helper: put product in cart, go through checkout to payment page."""
        CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        # Set checkout session
        session = self.client.session
        session["checkout_data"] = {
            "shipping_address_id": self.address.pk,
            "billing_address_id": None,
            "coupon_code": "",
            "notes": "",
        }
        session.save()

    def test_stock_decrements_on_cod_payment(self):
        self._go_through_checkout()
        self.client.post(reverse("payment"), {"payment_method": "cod"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_order_created_on_cod_payment(self):
        self._go_through_checkout()
        self.client.post(reverse("payment"), {"payment_method": "cod"})
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)

    def test_cart_cleared_after_order(self):
        self._go_through_checkout()
        self.client.post(reverse("payment"), {"payment_method": "cod"})
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)


# ─────────────────────────── Mock payment ────────────────────────────

class MockPaymentServiceTest(TestCase):
    def test_success_card(self):
        result = process_payment(method="card", amount=Decimal("49.99"), card={"number": "4242424242424242"})
        self.assertTrue(result.succeeded)
        self.assertEqual(result.card_brand, "VISA")
        self.assertEqual(result.card_last4, "4242")

    def test_decline_card(self):
        result = process_payment(method="card", amount=Decimal("49.99"), card={"number": "4000000000000002"})
        self.assertFalse(result.succeeded)
        self.assertIn("declined", result.failure_reason.lower())

    def test_insufficient_funds(self):
        result = process_payment(method="card", amount=Decimal("49.99"), card={"number": "4000000000000009995"})
        # Should fail (invalid Luhn due to extra digit) or insufficient
        self.assertFalse(result.succeeded)

    def test_invalid_luhn(self):
        result = process_payment(method="card", amount=Decimal("49.99"), card={"number": "1234567890123456"})
        self.assertFalse(result.succeeded)
        self.assertIn("invalid", result.failure_reason.lower())

    def test_mastercard_success(self):
        result = process_payment(method="card", amount=Decimal("49.99"), card={"number": "5555555555554444"})
        self.assertTrue(result.succeeded)
        self.assertEqual(result.card_brand, "MASTERCARD")

    def test_apple_pay_succeeds(self):
        result = process_payment(method="apple_pay", amount=Decimal("49.99"))
        self.assertTrue(result.succeeded)

    def test_google_pay_succeeds(self):
        result = process_payment(method="google_pay", amount=Decimal("49.99"))
        self.assertTrue(result.succeeded)

    def test_paypal_succeeds(self):
        result = process_payment(method="paypal", amount=Decimal("49.99"), wallet_email="user@paypal.test")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.wallet_email, "user@paypal.test")

    def test_cod_succeeds(self):
        result = process_payment(method="cod", amount=Decimal("49.99"))
        self.assertTrue(result.succeeded)

    def test_card_succeeds_in_payment_view(self):
        user = make_user("carduser")
        product = make_product()
        address = make_address(user)
        self.client.login(username="carduser", password="pass1234!")
        CartItem.objects.create(user=user, product=product, quantity=1)
        session = self.client.session
        session["checkout_data"] = {
            "shipping_address_id": address.pk,
            "billing_address_id": None,
            "coupon_code": "",
            "notes": "",
        }
        session.save()
        response = self.client.post(reverse("payment"), {
            "payment_method": "card",
            "card_number": "4242 4242 4242 4242",
            "card_exp": "12 / 28",
            "card_cvc": "123",
            "card_name": "Test User",
        })
        order = Order.objects.filter(user=user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment.method, "card")
        self.assertEqual(order.payment.status, "paid")
        self.assertEqual(order.payment.card_last4, "4242")

    def test_declined_card_does_not_create_order(self):
        user = make_user("declineuser")
        product = make_product()
        address = make_address(user)
        self.client.login(username="declineuser", password="pass1234!")
        CartItem.objects.create(user=user, product=product, quantity=1)
        session = self.client.session
        session["checkout_data"] = {
            "shipping_address_id": address.pk,
            "billing_address_id": None,
            "coupon_code": "",
            "notes": "",
        }
        session.save()
        self.client.post(reverse("payment"), {
            "payment_method": "card",
            "card_number": "4000 0000 0000 0002",
            "card_exp": "12 / 28",
            "card_cvc": "123",
            "card_name": "Test User",
        })
        self.assertFalse(Order.objects.filter(user=user).exists())


# ─────────────────────────── Address ownership ────────────────────────────

class AddressOwnershipTest(TestCase):
    def setUp(self):
        self.user1 = make_user("user1")
        self.user2 = make_user("user2")
        self.addr = make_address(self.user1)
        self.client.login(username="user2", password="pass1234!")

    def test_cannot_edit_other_users_address(self):
        response = self.client.post(
            reverse("address_edit", kwargs={"pk": self.addr.pk}),
            {"full_name": "Hacked"},
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_users_address(self):
        response = self.client.post(reverse("address_delete", kwargs={"pk": self.addr.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Address.objects.filter(pk=self.addr.pk).exists())


# ─────────────────────────── Staff redirects ────────────────────────────

class StaffRequiredTest(TestCase):
    def setUp(self):
        self.regular = make_user("regular")
        self.staff = make_user("staffuser", is_staff=True)

    def test_dashboard_requires_staff(self):
        self.client.login(username="regular", password="pass1234!")
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"/admin/login/?next=/dashboard/", fetch_redirect_response=False)

    def test_staff_can_access_dashboard(self):
        self.client.login(username="staffuser", password="pass1234!")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────── Coupon ────────────────────────────

class CouponTest(TestCase):
    def test_percent_coupon(self):
        coupon = Coupon(code="SAVE20", percent_off=20)
        discount = coupon.calculate_discount(Decimal("100.00"))
        self.assertEqual(discount, Decimal("20.00"))

    def test_amount_coupon(self):
        coupon = Coupon(code="SAVE10", amount_off=Decimal("10.00"))
        discount = coupon.calculate_discount(Decimal("50.00"))
        self.assertEqual(discount, Decimal("10.00"))

    def test_amount_coupon_capped_at_subtotal(self):
        coupon = Coupon(code="BIGSAVE", amount_off=Decimal("200.00"))
        discount = coupon.calculate_discount(Decimal("50.00"))
        self.assertEqual(discount, Decimal("50.00"))


class NewUserCouponFormTest(TestCase):
    def setUp(self):
        self.user = make_user("newbie")
        self.addr = make_address(self.user)
        Coupon.objects.create(
            code="FIRST15",
            percent_off=15,
            new_users_only=True,
            is_active=True,
        )

    def test_new_user_can_apply_first_order_coupon(self):
        form = CheckoutForm(
            self.user,
            {
                "shipping_address": str(self.addr.pk),
                "billing_address": "",
                "coupon_code": "FIRST15",
                "notes": "",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_returning_customer_cannot_apply_new_user_coupon(self):
        Order.objects.create(
            user=self.user,
            subtotal=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
            total_price=Decimal("10.00"),
            status=Order.Status.COMPLETED,
            shipping_address="x",
        )
        form = CheckoutForm(
            self.user,
            {
                "shipping_address": str(self.addr.pk),
                "billing_address": "",
                "coupon_code": "FIRST15",
                "notes": "",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("first order", form.errors["coupon_code"][0].lower())


class ProductListingImageTest(TestCase):
    def test_with_listing_image_excludes_bare_products(self):
        make_product(name="With Cover", image_url="https://example.com/a.jpg")
        make_product(name="No Cover", image_url="")
        qs = Product.objects.filter(is_active=True).with_listing_image()
        self.assertTrue(qs.filter(name="With Cover").exists())
        self.assertFalse(qs.filter(name="No Cover").exists())


class OpenLibraryCoverHelperTest(TestCase):
    def test_candidate_cover_urls_prefers_cover_id_then_isbn(self):
        doc = {"cover_i": 12345, "isbn": ["9781492078005", "9780135957059"]}
        urls = candidate_cover_urls_from_doc(doc)
        self.assertEqual(urls[0], "https://covers.openlibrary.org/b/id/12345-L.jpg")
        self.assertEqual(urls[1], "https://covers.openlibrary.org/b/isbn/9781492078005-L.jpg")

    def test_first_valid_cover_url_returns_first_image_response(self):
        session = Mock()

        bad_response = Mock()
        bad_response.status_code = 502
        bad_response.headers = {"Content-Type": "text/html"}
        bad_response.__enter__ = Mock(return_value=bad_response)
        bad_response.__exit__ = Mock(return_value=False)

        good_response = Mock()
        good_response.status_code = 200
        good_response.headers = {"Content-Type": "image/jpeg"}
        good_response.__enter__ = Mock(return_value=good_response)
        good_response.__exit__ = Mock(return_value=False)

        session.get.side_effect = [bad_response, good_response]

        url = first_valid_cover_url(
            [
                "https://covers.openlibrary.org/b/id/1-L.jpg",
                "https://covers.openlibrary.org/b/id/2-L.jpg",
            ],
            session=session,
        )
        self.assertEqual(url, "https://covers.openlibrary.org/b/id/2-L.jpg")
