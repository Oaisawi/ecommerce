# Epic AI Reads

Epic AI Reads is a Django-based bookstore web application focused on AI, machine learning, deep learning, and related technical books. The project includes a public storefront, cart and checkout flow, mock payment processing, staff/admin inventory tools, and production deployment support.

Live deployment:
- Render URL: `https://epic-ai-reads.onrender.com`
- Custom domain: `https://webais.dev`

## Application Details

Core capabilities:
- User registration, login, logout, and profile management
- Product catalog with categories, search, filtering, sorting, and featured/on-sale sections
- Product image upload support plus external image URL fallback
- Shopping cart, checkout review, shipping and billing address capture
- Mock payment flow with card, Apple Pay, Google Pay, PayPal, and cash on delivery
- Order confirmation, order history, and pre-processing order cancellation
- Coupon support, new-user coupon support, and review/rating support
- Staff dashboard for product management, stock adjustments, inventory warnings, and order status updates
- Seed/demo data commands and deployment support for Render

Main application areas:
- `commerce_site/`: project settings, WSGI, URLs
- `store/`: models, views, forms, admin, custom management commands
- `templates/`: public pages, admin-facing pages, and email templates
- `static/`: Tailwind source/build output and JavaScript assets

## Tech Stack

- Python 3.12
- Django 4.2
- SQLite for default local development
- PostgreSQL or MySQL through `DATABASE_URL` for production or alternate local setups
- Tailwind CSS for frontend styling
- WhiteNoise for static file serving
- Gunicorn for production app serving

## Dependencies

Python packages from [requirements.txt](/c:/Users/Salem/OneDrive/Documents/WebDevProject/requirements.txt):
- `Django`
- `python-dotenv`
- `dj-database-url`
- `whitenoise`
- `gunicorn`
- `Pillow`
- `requests`
- `PyMySQL`
- `psycopg2-binary`

Frontend packages from [package.json](/c:/Users/Salem/OneDrive/Documents/WebDevProject/package.json):
- `tailwindcss`
- `@tailwindcss/forms`
- `@tailwindcss/typography`

## Local Setup

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- `pip`
- `npm`

### Setup Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd WebDevProject

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install frontend dependencies
npm install

# 5. Create environment file
copy .env.example .env
# macOS / Linux: cp .env.example .env

# 6. Build CSS
npm run build:css

# 7. Run migrations
python manage.py migrate

# 8. Optional: create an admin user locally
python manage.py createsuperuser

# 9. Optional: seed demo books
python manage.py seed_ai_books

# 10. Start the development server
python manage.py runserver
```

Open:
- `http://127.0.0.1:8000`
- Django admin: `http://127.0.0.1:8000/admin/`

## Environment Configuration

The project uses `.env` values loaded from [commerce_site/settings.py](/c:/Users/Salem/OneDrive/Documents/WebDevProject/commerce_site/settings.py).

Important variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True` for local development, `False` for production
- `ALLOWED_HOSTS`: comma-separated hostnames
- `DATABASE_URL`: blank for SQLite, or a PostgreSQL/MySQL connection string
- `CSRF_TRUSTED_ORIGINS`: comma-separated HTTPS origins
- `STORE_CURRENCY`
- `STORE_CURRENCY_SYMBOL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

See [\.env.example](/c:/Users/Salem/OneDrive/Documents/WebDevProject/.env.example) for the full template.

## Database Setup

Default behavior:
- If `DATABASE_URL` is blank, Django uses SQLite (`db.sqlite3`)
- If `DATABASE_URL` is set, Django uses that database through `dj-database-url`

Database reference files added for this project:
- [database/SCHEMA.md](/c:/Users/Salem/OneDrive/Documents/WebDevProject/database/SCHEMA.md): schema overview and table descriptions
- [database/sql/create_local_mysql_database.sql](/c:/Users/Salem/OneDrive/Documents/WebDevProject/database/sql/create_local_mysql_database.sql): optional MySQL database/bootstrap SQL
- [database/sql/create_local_postgres_database.sql](/c:/Users/Salem/OneDrive/Documents/WebDevProject/database/sql/create_local_postgres_database.sql): optional PostgreSQL database/bootstrap SQL

Important note:
- Django migrations are the source of truth for table creation and schema updates
- The SQL files provision the database itself; application tables are created by `python manage.py migrate`

## Seed and Admin Commands

Useful commands:

```bash
# Seed demo AI books from OpenLibrary
python manage.py seed_ai_books

# Repair missing or broken product cover URLs
python manage.py backfill_book_covers --all

# Create a deploy-time admin user from env vars if missing
python manage.py create_admin_if_missing
```

## Mock Payment Details

This project does not use a real payment gateway. Payments are simulated and stored in the database.

Supported test methods:
- Credit/debit card
- Apple Pay
- Google Pay
- PayPal
- Cash on Delivery

Example card numbers:

| Card Number | Result |
|---|---|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 0002` | Declined |
| `4000 0000 0000 9995` | Insufficient funds |
| `5555 5555 5555 4444` | Success |

## Testing

Run the test suite:

```bash
python manage.py test store
```

Current tests cover:
- cart calculations
- checkout and payment flow behavior
- stock decrement and inventory updates
- address ownership restrictions
- staff access restrictions
- coupon logic
- listing image helpers

## Deployment

### Render Deployment

This project is configured for Render using [render.yaml](/c:/Users/Salem/OneDrive/Documents/WebDevProject/render.yaml).

Deployment flow:
1. Push the repository to GitHub.
2. In Render, create a new `Blueprint`.
3. Select this repository.
4. Render provisions the web service and PostgreSQL database.
5. Render runs the build script from [build.sh](/c:/Users/Salem/OneDrive/Documents/WebDevProject/build.sh).

Build script behavior:

```bash
bash build.sh
```

The build script:
- installs Python packages
- runs `collectstatic`
- runs migrations
- runs `create_admin_if_missing`

Production server command:

```bash
gunicorn commerce_site.wsgi:application
```

### Production Checklist

- Set `DEBUG=False`
- Configure `SECRET_KEY`
- Configure `DATABASE_URL`
- Configure `ALLOWED_HOSTS`
- Configure `CSRF_TRUSTED_ORIGINS`
- Configure email variables if SMTP email is required
- Set `DJANGO_SUPERUSER_*` env vars before the first deploy if you want the initial admin created automatically
- Remove `DJANGO_SUPERUSER_PASSWORD` after the first successful deploy

### Custom Domain

The deployed site supports:
- `webais.dev`
- `www.webais.dev`

If using a custom domain, make sure:
- DNS records point to Render
- `ALLOWED_HOSTS=webais.dev,www.webais.dev`
- `CSRF_TRUSTED_ORIGINS=https://webais.dev,https://www.webais.dev`

For more deployment detail, see [RENDER_DEPLOY.md](/c:/Users/Salem/OneDrive/Documents/WebDevProject/RENDER_DEPLOY.md).

## Project Structure

```text
commerce_site/                     Django project settings and configuration
store/                             Main application: models, views, forms, admin, commands
store/management/commands/         Seed, admin bootstrap, and utility commands
templates/                         HTML templates
static/                            CSS, JS, and static assets
database/                          Schema reference and SQL bootstrap files
render.yaml                        Render blueprint
build.sh                           Production build script
requirements.txt                   Python dependencies
package.json                       Frontend build dependencies
```
