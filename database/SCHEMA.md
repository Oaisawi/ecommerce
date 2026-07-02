# Database Schema

This document describes the main application schema for Epic AI Reads.

Important:
- Django migrations are the source of truth for the live schema
- Table names below reflect Django's default naming conventions
- The built-in Django auth/admin/session tables are also required but are not exhaustively listed here

## Core Application Tables

### `store_category`

Purpose:
- Stores product categories

Key fields:
- `id`
- `name` unique
- `slug` unique
- `description`
- `created_at`

Relationships:
- one-to-many with `store_product`

### `store_product`

Purpose:
- Stores books/products shown in the storefront

Key fields:
- `id`
- `name`
- `subtitle`
- `author`
- `isbn`
- `publisher`
- `published_date`
- `pages`
- `language`
- `format`
- `description`
- `price`
- `sale_price`
- `stock`
- `image`
- `image_url`
- `is_active`
- `is_featured`
- `slug` unique
- `rating_avg`
- `rating_count`
- `created_at`
- `updated_at`
- `category_id` nullable foreign key to `store_category`

Relationships:
- many-to-one with `store_category`
- one-to-many with `store_review`
- one-to-many with `store_stockadjustment`
- one-to-many with `store_cartitem`
- one-to-many with `store_orderitem`

### `store_review`

Purpose:
- Stores user reviews for products

Key fields:
- `id`
- `rating`
- `comment`
- `created_at`
- `product_id` foreign key to `store_product`
- `user_id` foreign key to `auth_user`

Constraints:
- unique review per `(user_id, product_id)`

### `store_coupon`

Purpose:
- Stores discount coupons

Key fields:
- `id`
- `code` unique
- `percent_off`
- `amount_off`
- `max_uses`
- `used_count`
- `expires_at`
- `is_active`
- `new_users_only`
- `created_at`

### `store_stockadjustment`

Purpose:
- Stores manual and automatic stock history records

Key fields:
- `id`
- `quantity_change`
- `reason`
- `note`
- `created_at`
- `product_id` foreign key to `store_product`
- `created_by_id` nullable foreign key to `auth_user`

### `store_cartitem`

Purpose:
- Stores shopping cart lines per user

Key fields:
- `id`
- `quantity`
- `created_at`
- `updated_at`
- `user_id` foreign key to `auth_user`
- `product_id` foreign key to `store_product`

Constraints:
- unique cart item per `(user_id, product_id)`

### `store_address`

Purpose:
- Stores shipping and billing addresses for users

Key fields:
- `id`
- `type`
- `full_name`
- `street_address`
- `city`
- `state`
- `postal_code`
- `country`
- `phone`
- `is_default`
- `created_at`
- `user_id` foreign key to `auth_user`

### `store_order`

Purpose:
- Stores customer orders

Key fields:
- `id`
- `subtotal`
- `discount_amount`
- `total_price`
- `status`
- `shipping_address`
- `billing_address`
- `notes`
- `created_at`
- `updated_at`
- `user_id` foreign key to `auth_user`
- `coupon_id` nullable foreign key to `store_coupon`

### `store_orderitem`

Purpose:
- Stores order line items

Key fields:
- `id`
- `product_name`
- `product_author`
- `unit_price`
- `quantity`
- `order_id` foreign key to `store_order`
- `product_id` nullable foreign key to `store_product`

### `store_payment`

Purpose:
- Stores mock payment records associated with orders

Key fields:
- `id`
- `method`
- `status`
- `amount`
- `txn_id`
- `card_brand`
- `card_last4`
- `wallet_email`
- `failure_reason`
- `created_at`
- `order_id` one-to-one foreign key to `store_order`

## Django Built-In Tables

The following Django-managed tables are also required:
- `auth_user`
- `auth_group`
- `auth_permission`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`

## Schema Creation

Recommended setup flow:
1. Create the database using one of the SQL bootstrap files in `database/sql/`
2. Set `DATABASE_URL`
3. Run:

```bash
python manage.py migrate
```

That command creates all Django and application tables using migrations.
