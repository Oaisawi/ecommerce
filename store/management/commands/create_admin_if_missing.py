import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from env vars if it does not already exist."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            self.stdout.write(
                "Skipping admin bootstrap: DJANGO_SUPERUSER_USERNAME and "
                "DJANGO_SUPERUSER_PASSWORD are not both set."
            )
            return

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user:
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if email and user.email != email:
                user.email = email
                changed = True
            if changed:
                user.save(update_fields=["is_staff", "is_superuser", "email"] if email else ["is_staff", "is_superuser"])
                self.stdout.write(self.style.SUCCESS(f"Updated existing admin user '{username}'"))
            else:
                self.stdout.write(f"Admin user '{username}' already exists")
            return

        create_kwargs = {
            "username": username,
            "password": password,
        }
        if email:
            create_kwargs["email"] = email
        User.objects.create_superuser(**create_kwargs)
        self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'"))
