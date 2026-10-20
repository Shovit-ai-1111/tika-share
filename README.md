# Dashain Tika & Jamara 🌼

A small Django app. Upload your photo and your payment QR, get a link, and send it to a friend.
Your friend opens the link, drags the **tika** and **jamara** onto your face, presses **Done**,
and your **QR pops up**.

- **Create your own** button in the header: anyone can add their own photo + QR screenshot.
- **Django admin** (`/admin/`): you can add cards yourself (photo + QR), tick **Featured** to show a card
  on the home page, untick **Active** to disable a link, and delete any card.
- Works with mouse and touch (drag), or just tap the tika / jamara. Keyboard friendly too.

## Run it with Docker

```bash
cp .env.example .env        # then edit ADMIN_PASSWORD (and DJANGO_SECRET_KEY for production)
docker compose up --build
```

Open <http://localhost:8000>. Admin: <http://localhost:8000/admin/> with `ADMIN_USERNAME` /
`ADMIN_PASSWORD` from your `.env` (created automatically on first start).

The database and uploaded images live in the `tika_data` Docker volume, so they survive restarts
and rebuilds. `docker compose down -v` deletes them.

> With no `.env`, a development login `admin` / `admin12345` is used and `DJANGO_DEBUG=1`.
> The app **refuses to start in production mode** (`DJANGO_DEBUG=0`) with the default secret key
> or the default admin password.

## Sharing with friends outside your Wi-Fi

`localhost` links only work on your own computer. To give friends a working link, the app must be
reachable on the internet: deploy it to a server, or use a tunnel (Cloudflare Tunnel, ngrok, ...).
Then set in `.env`:

```
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<long random string>
DJANGO_ALLOWED_HOSTS=tika.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://tika.example.com
DJANGO_BEHIND_PROXY=1            # when an HTTPS proxy/tunnel sits in front
PUBLIC_BASE_URL=https://tika.example.com
```

## How it works

| Page | URL | Who |
|---|---|---|
| Home | `/` | everyone |
| Create your own | `/create/` | everyone |
| Share link page | `/c/<id>/share/` | the creator (same browser) |
| Friend page (tika, jamara, Done, QR) | `/c/<id>/` | anyone with the link |
| My cards | `/my/` | the creator (same browser) |
| Admin | `/admin/` | you |

- Each card gets a random 8-character id, so links can't be guessed by counting.
- Creators don't need an account: the browser session remembers which cards they made, which is what
  lets them reopen the share page and delete their card. If they clear their cookies, only you (admin)
  can delete it.
- Uploaded images are re-encoded: photos become JPEG (max 1600 px), QR screenshots stay lossless PNG.
  GPS/EXIF data is stripped, phone rotation is applied, and non-images (including SVG) are rejected.
  Max upload size is 8 MB.

## Good to know

- **Anyone with a link can see that person's photo and QR.** The create page says so. Don't share
  links publicly if you don't want the QR seen.
- Uploaded files are served by Django, which is fine for a family/friends app. For heavy traffic put
  nginx or object storage in front.
- SQLite is used for simplicity. Back up the `tika_data` volume if the cards matter to you.
- The tika and jamara pictures are SVGs in `cards/static/cards/img/`. Replace them with your own
  artwork (same file names) if you like. Default sizes/positions are in `cards/static/cards/js/tika.js`.

## Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Tests

```bash
python manage.py test cards
```

## Layout

```
config/                 settings, urls, wsgi
cards/models.py         Card (photo, QR, featured/active flags, random slug)
cards/images.py         upload validation + re-encoding
cards/views.py          home, create, share, friend page, my cards, delete
cards/admin.py          admin with thumbnails + share links
cards/templates/        HTML
cards/static/cards/     css, js (tika.js = drag & drop), svg art
cards/tests.py          27 tests
Dockerfile, docker-compose.yml, entrypoint.sh, .env.example
```
