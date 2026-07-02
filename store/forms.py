from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Address, Category, Coupon, Order, Product, Review, StockAdjustment


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "subtitle", "author", "isbn", "category",
            "publisher", "published_date", "pages", "language", "format",
            "description", "price", "sale_price", "stock",
            "image", "image_url", "is_active", "is_featured",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "published_date": forms.DateInput(attrs={"type": "date"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ["quantity_change", "reason", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional note..."}),
        }


class CartAddForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["type", "full_name", "street_address", "city", "state", "postal_code", "country", "phone", "is_default"]
        widgets = {
            "street_address": forms.Textarea(attrs={"rows": 2}),
        }


class CheckoutForm(forms.Form):
    """Step 1 of checkout — shipping & billing address + notes only. No payment fields."""
    shipping_address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        empty_label="Select shipping address…",
    )
    billing_address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        required=False,
        empty_label="Same as shipping (optional)",
    )
    coupon_code = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "Coupon code (optional)"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Special instructions (optional)"}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields["shipping_address"].queryset = Address.objects.filter(user=user, type=Address.Type.SHIPPING)
        self.fields["billing_address"].queryset = Address.objects.filter(user=user, type=Address.Type.BILLING)

    def clean_coupon_code(self):
        code = self.cleaned_data.get("coupon_code", "").strip()
        if not code:
            return ""
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            raise forms.ValidationError("Coupon code not found.") from None
        if not coupon.is_valid():
            raise forms.ValidationError("This coupon is expired or no longer valid.")
        if not coupon.user_may_redeem(self._user):
            raise forms.ValidationError("This coupon is only for your first order with us.")
        return code


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Share your thoughts on this book…"}),
        }


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
