from django.db import migrations, models


def seed_welcome15(apps, schema_editor):
    Coupon = apps.get_model("store", "Coupon")
    Coupon.objects.update_or_create(
        code="WELCOME15",
        defaults={
            "percent_off": 15,
            "amount_off": None,
            "max_uses": 0,
            "is_active": True,
            "new_users_only": True,
        },
    )


def unseed_welcome15(apps, schema_editor):
    Coupon = apps.get_model("store", "Coupon")
    Coupon.objects.filter(code__iexact="WELCOME15").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0003_book_fields_review_coupon_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="coupon",
            name="new_users_only",
            field=models.BooleanField(
                default=False,
                help_text="If checked, only customers who have never placed an order may use this code.",
            ),
        ),
        migrations.RunPython(seed_welcome15, unseed_welcome15),
    ]
