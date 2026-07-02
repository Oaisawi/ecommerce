from django.urls import path

from . import views

urlpatterns = [
    # Public
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("books/<slug:slug>/", views.product_detail, name="product_detail"),
    path("books/<slug:slug>/add-to-cart/", views.add_to_cart, name="add_to_cart"),

    # Cart
    path("cart/", views.cart, name="cart"),
    path("cart/items/<int:pk>/update/", views.update_cart_item, name="update_cart_item"),
    path("cart/items/<int:pk>/remove/", views.remove_cart_item, name="remove_cart_item"),

    # Checkout flow
    path("cart/checkout/", views.checkout, name="checkout"),
    path("cart/payment/", views.payment, name="payment"),

    # Orders
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:pk>/confirm/", views.order_confirmation, name="order_confirmation"),

    # Profile
    path("profile/", views.profile, name="profile"),
    path("profile/addresses/new/", views.address_create, name="address_create"),
    path("profile/addresses/<int:pk>/edit/", views.address_edit, name="address_edit"),
    path("profile/addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),

    # Staff dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/products/new/", views.product_create, name="product_create"),
    path("dashboard/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("dashboard/products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("dashboard/products/<int:pk>/stock/", views.stock_adjust, name="stock_adjust"),
    path("dashboard/categories/", views.category_list, name="category_list"),
    path("dashboard/categories/new/", views.category_create, name="category_create"),
    path("dashboard/categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("dashboard/orders/", views.order_management, name="order_management"),
    path("dashboard/orders/<int:pk>/", views.order_manage_detail, name="order_manage_detail"),
]
