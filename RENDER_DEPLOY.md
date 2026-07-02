# Render Deployment

This project is ready to deploy on Render with the included `render.yaml`.

## What Was Added

- `render.yaml` provisions:
  - one Python web service
  - one PostgreSQL database
  - `DATABASE_URL` wired from the database to the app
  - generated `SECRET_KEY`
  - `DEBUG=False`
- `commerce_site/settings.py` now auto-adds Render's `RENDER_EXTERNAL_HOSTNAME` to:
  - `ALLOWED_HOSTS`
  - `CSRF_TRUSTED_ORIGINS`

That means the default Render URL will work even if you leave those vars unset.

## Deploy From GitHub

1. Push this repo to GitHub.
2. In Render, click `New +` -> `Blueprint`.
3. Select this repository.
4. Render will detect `render.yaml` and show:
   - web service: `epic-ai-reads`
   - database: `epic-ai-reads-db`
5. Confirm and create the blueprint.

## Build And Start Behavior

Render will run this build command:

```bash
bash build.sh
```

Render will start the app with:

```bash
gunicorn commerce_site.wsgi:application
```

## Environment Variables

Render already sets these from `render.yaml`:

- `SECRET_KEY`
- `DEBUG=False`
- `DATABASE_URL`
- `PYTHON_VERSION=3.12.7`

Optional variables you can add in Render if needed:

- `ALLOWED_HOSTS`
  Example: `your-custom-domain.com,www.your-custom-domain.com`
- `CSRF_TRUSTED_ORIGINS`
  Example: `https://your-custom-domain.com,https://www.your-custom-domain.com`
- `STORE_CURRENCY`
- `STORE_CURRENCY_SYMBOL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`

## Custom Domain

If you add a custom domain in Render:

1. Attach the domain in the Render service settings.
2. Add that domain to `ALLOWED_HOSTS`.
3. Add the `https://` version to `CSRF_TRUSTED_ORIGINS`.

Example:

```text
ALLOWED_HOSTS=books.example.com,www.books.example.com
CSRF_TRUSTED_ORIGINS=https://books.example.com,https://www.books.example.com
```

## First Login

This project supports creating the first admin user during deploy without Render shell access.

Set these environment variables in the Render web service before deploying:

```text
DJANGO_SUPERUSER_USERNAME=your-admin-name
DJANGO_SUPERUSER_EMAIL=you@example.com
DJANGO_SUPERUSER_PASSWORD=choose-a-strong-password
```

During deploy, `build.sh` runs:

```bash
python manage.py create_admin_if_missing
```

Behavior:

- if the username does not exist, a new superuser is created
- if the username already exists, it is ensured to be `is_staff=True` and `is_superuser=True`

After the first successful deploy, remove `DJANGO_SUPERUSER_PASSWORD` from Render.

## Important Notes

- Do not use SQLite on Render for production. The included blueprint provisions PostgreSQL instead.
- Static files are served by WhiteNoise after `collectstatic`.
- Your local `.env` is not uploaded to Render. Add production-only secrets in the Render dashboard.
