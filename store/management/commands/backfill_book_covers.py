import time

from django.core.management.base import BaseCommand

from store.models import Product
from store.openlibrary import (
    build_session,
    candidate_cover_urls_from_doc,
    first_valid_cover_url,
    search_book_docs,
)


class Command(BaseCommand):
    help = "Backfill or repair Product.image_url values using OpenLibrary lookups."

    def _safe_log(self, message, style=None):
        rendered = style(message) if style else message
        try:
            self.stdout.write(rendered)
        except UnicodeEncodeError:
            self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Only process up to N products. Default: all matching products.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Revalidate all products, not just those missing image_url.",
        )

    def handle(self, *args, **options):
        session = build_session()
        queryset = Product.objects.order_by("pk")
        if not options["all"]:
            queryset = queryset.filter(image_url="")

        limit = options["limit"]
        if limit:
            queryset = queryset[:limit]

        updated = 0
        skipped = 0
        failed = 0

        for product in queryset:
            current_url = (product.image_url or "").strip()
            if current_url and first_valid_cover_url([current_url], session=session):
                skipped += 1
                self._safe_log(f"Skipped: {product.name[:60]} (existing image still valid)")
                continue

            replacement_url = ""
            try:
                docs = search_book_docs(product.name, product.author, session=session, limit=5)
            except Exception as exc:
                failed += 1
                self._safe_log(f"Lookup failed for {product.name[:60]}: {exc}", style=self.style.ERROR)
                continue

            for doc in docs:
                replacement_url = first_valid_cover_url(candidate_cover_urls_from_doc(doc), session=session)
                if replacement_url:
                    break

            if product.isbn and not replacement_url:
                replacement_url = first_valid_cover_url(
                    [f"https://covers.openlibrary.org/b/isbn/{product.isbn}-L.jpg"],
                    session=session,
                )

            if replacement_url:
                product.image_url = replacement_url
                product.save(update_fields=["image_url", "updated_at"])
                updated += 1
                self._safe_log(f"Updated: {product.name[:60]}", style=self.style.SUCCESS)
            else:
                failed += 1
                self._safe_log(f"No valid cover found: {product.name[:60]}", style=self.style.WARNING)

            time.sleep(0.2)

        self._safe_log(
            f"Backfill finished. Updated={updated}, Skipped={skipped}, Failed={failed}",
            style=self.style.SUCCESS,
        )
