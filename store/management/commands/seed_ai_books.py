import random
import time

from django.core.management.base import BaseCommand

from store.models import Category, Product
from store.openlibrary import build_session, candidate_cover_urls_from_doc, first_valid_cover_url


class Command(BaseCommand):
    help = "Fetches 100 real AI books from OpenLibrary API and populates the database."

    def _safe_log(self, message, style=None):
        rendered = style(message) if style else message
        try:
            self.stdout.write(rendered)
        except UnicodeEncodeError:
            self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

    def handle(self, *args, **options):
        topics = [
            "machine_learning",
            "deep_learning",
            "natural_language_processing",
            "artificial_intelligence",
            "computer_vision",
        ]

        session = build_session()
        books_created = 0
        target_books = 100

        self._safe_log("Starting to fetch books from OpenLibrary API...")

        for topic in topics:
            display_topic = topic.replace("_", " ").title()
            category, _ = Category.objects.get_or_create(
                name=display_topic,
                defaults={"slug": topic},
            )

            # OpenLibrary search API
            page = 1

            while books_created < target_books and page < 5:
                url = f"https://openlibrary.org/search.json?subject={topic}&page={page}&limit=20"
                try:
                    response = session.get(url, timeout=12)
                    response.raise_for_status()
                    data = response.json()

                    items = data.get("docs", [])
                    if not items:
                        break  # No more results for this topic

                    for item in items:
                        if books_created >= target_books:
                            break

                        # Skip if essential info is missing
                        if "title" not in item or "author_name" not in item:
                            continue

                        title = item["title"]

                        # Skip if already exists
                        if Product.objects.filter(name=title).exists():
                            continue

                        author = ", ".join(item.get("author_name", ["Unknown"]))

                        isbn = ""
                        if "isbn" in item and len(item["isbn"]) > 0:
                            isbn = item["isbn"][0]

                        image_url = first_valid_cover_url(candidate_cover_urls_from_doc(item), session=session)

                        description = f"A comprehensive guide on {display_topic} by {author}."
                        if "first_publish_year" in item:
                            description += f" First published in {item['first_publish_year']}."

                        # Realistic pricing between $29.99 and $149.99 for AI books
                        price = round(random.uniform(29.99, 149.99), 2)
                        stock = random.randint(5, 50)

                        Product.objects.create(
                            name=title[:200],
                            author=author[:200],
                            isbn=isbn[:20],
                            description=description,
                            price=price,
                            stock=stock,
                            category=category,
                            image_url=image_url,
                        )
                        books_created += 1
                        self._safe_log(
                            f"[{books_created}/{target_books}] Created: {title[:50]}...",
                            style=self.style.SUCCESS,
                        )

                    page += 1
                    time.sleep(1)  # Be nice to the API

                except Exception as e:
                    self._safe_log(f"Error fetching data: {e}", style=self.style.ERROR)
                    break

            if books_created >= target_books:
                break

        self._safe_log(f"Successfully seeded {books_created} books!", style=self.style.SUCCESS)
