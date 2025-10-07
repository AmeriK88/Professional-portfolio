# JFGC · Dev — Full‑Stack Services Platform (Django)

A production‑ready platform to **sell software services**, take **Pi Network payments**, and manage customer communication end‑to‑end. Built with **Django**, **Bootstrap**, and **django‑unfold** for a sleek admin.

---

## ✨ Highlights

- **Services marketplace** with rich detail pages, FAQs, features, and media previews.
- **Orders & checkout** in EUR with **on‑the‑fly conversion to π** (configurable `PI_EUR_PER_PI`).
- **Pi Network payments** (approve / complete / cancel / webhook) with robust reconciliation and idempotency.
- **Inbox** per order for system/user/admin messaging.
- **Blog + Projects** with preview compression via **FFmpeg**.
- **Auth**: classic username/password + **Pi Login**; **reCAPTCHA v3** on auth flows.
- Hardened **security**: `django-axes`, strict cookies/HSTS in prod, sandbox middleware for Pi iFrame.
- Polished **admin** using **django‑unfold** (bulk actions, badges, filters, pretty JSON, thumbnails).
- Thoughtful **SEO/PWA**: OpenGraph/Twitter tags, canonical links, minimal service worker.

---

## 🏗️ Architecture & Apps

```
core/          Home, legal pages, sandbox middleware, base templates
blog/          Simple CMS (Post) + list/detail + admin thumbnails
projects/      Portfolio projects with preview compression (signals/admin)
services/      Sellable services (+ features, FAQs), list/detail, payment success
orders/        Order & OrderItem, checkout, list/detail, totals in EUR
pi_payments/   Payment model + views (approve/complete/cancel/webhook), admin tools
inbox/         Per‑order thread + messages (system/user/admin) + unread badge
users/         Custom User, profile edit, Pi login, CV download, auth flows
portfolio/     Project URLs, settings, admin dashboard, WSGI
```

### Data Flow (Happy Path)

1. **Browse services** → `services:list` / `services:detail`.
2. **Checkout (POST)** → creates `Order` (EUR) + `Payment` (snapshots pricing) → returns Pi SDK payload where **`amount` is in π**.
3. **Pi SDK** calls server:
   - `/pi/approve/` → marks `Payment` *initiated* (links by metadata `order_number`).
   - `/pi/complete/` with `txid` → validates amount vs snapshot → marks `Payment` *confirmed* → cascades `Order` → *paid*.
   - `/pi/cancel/` (or insufficient balance) → marks *failed* and cancels order if not paid.
   - `/pi/webhook/` (optional) → reconciles late/duplicate events, idempotent by status/txid.
4. **Inbox** posts a system message on confirmed payment (signal).  
5. User sees **Orders** and **Payment success** receipt (IDs copy‑to‑clipboard, π/EUR breakdown).

---

## ⚙️ Requirements

- **Python 3.11+**
- **Django 4+** (project uses `django-environ`, `dj-database-url`, `django-axes`, `django-unfold`, `whitenoise`)
- **FFmpeg** in `$PATH` (used by `projects`/`services` signals & admin to compress preview MP4)
- A **database** (MySQL or Postgres). MySQL is supported via `mysqlclient` or **PyMySQL** shim.

> Previews: when you upload an MP4, a lightweight `*_s.mp4` is created (3s, 240px, 12fps, CRF 32, no audio) and the original is removed. Works locally (FileSystemStorage). For S3/GCS, move this to a background task or media pipeline.

---

## 🚀 Quick Start (Local)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # provide your lock/constraints file
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Ensure **FFmpeg** is installed (`ffmpeg -version`).  
- Visit `http://127.0.0.1:8000/admin/` for the admin (Unfold).  
- Default email backend prints to console (for password reset).

---

## 🔐 Environment & Settings

The project is driven by `.env`. Most important keys:

```env
# Core
DEBUG=true
SECRET_KEY=your-django-secret
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Database (either DATABASE_URL or explicit engine block)
DATABASE_URL=postgres://user:pass@host:5432/dbname
# or for MySQL: mysql://user:pass@host:3306/dbname
# If not using DATABASE_URL, set DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT

# Media & static
USE_VOLUME_MEDIA=false
FFMPEG_CMD=ffmpeg

# Pi payments
PI_API_KEY=your-pi-server-key
PI_EUR_PER_PI=0.30           # EUR per π (conversion rate used for pricing snapshot)
PI_ONLY_LOGIN=false          # force Pi-only login UI/flows if true
PI_SANDBOX=true              # relax headers for Pi Browser embedding in dev/sandbox

# reCAPTCHA v3
RECAPTCHA_SITE_KEY=your-site-key
RECAPTCHA_SECRET_KEY=your-secret-key
RECAPTCHA_MIN_SCORE=0.5
```

### Security & Cookies

- **Prod (`DEBUG=false`)**: `Secure` cookies, `SameSite=None`, **HSTS** enabled.
- **Dev (`DEBUG=true`)**: If using an HTTPS tunnel (`*.devtunnels.ms`/`*.ngrok.io`) cookies switch to `Secure` + `SameSite=None`. Otherwise `Lax` locally.
- Proxy friendly: `USE_X_FORWARDED_HOST=True`, `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")`.

### Pi Sandbox Middleware

`core.middleware.PiSandboxHeadersMiddleware` (enabled when `PI_SANDBOX` or `DEBUG`) adjusts headers so the app can run inside **Pi Browser** iframed:

- Unsets `X-Frame-Options`
- Extends CSP with allowed `frame-ancestors` for Pi
- Drops COOP/COEP/CORP that block cross‑origin iframes
- Adds `Permissions-Policy: payment=(self "https://*.minepi.com")`
- Marks responses with `X-Pi-Sandbox-MW: on`

> **Do not enable this in real production** unless you know you need iframe embedding for Pi Browser.

---

## 🧩 Notable Features by App

### `services`
- `Service` (price/image/preview, unique slug), `ServiceFeature`, `ServiceFAQ` with ordering.
- List & detail pages with **lazy video** or image preview and π estimation (`to_pi` filter).
- Admin actions: activate/deactivate, **recompress previews** (bulk/row).
- Signal compresses MP4 previews to `service_previews/*_s.mp4` idempotently.

### `orders`
- `Order` with `OrderItem`; totals in EUR. `get_absolute_url()` for detail.
- `checkout_service(slug)` creates order in EUR and a `Payment` with pricing snapshot; converts EUR→π using `PI_EUR_PER_PI` and returns Pi SDK payload (with `amount` in **π**).
- User **order list/detail** with π approximation.

### `pi_payments`
- Endpoints: `/pi/approve/`, `/pi/complete/`, `/pi/cancel/`, `/pi/webhook/`.
- Links Pi payment by reading `/v2/payments/<pid>` **metadata.order_number**.
- Validates **π amount** against the checkout snapshot, records **`txid`**, stores raw payloads & webhooks for audit.
- `Payment.mark_confirmed()` cascades `Order` → paid; `mark_failed()` cancels if not paid.
- Admin: one‑click **Sync from Pi**, status badges, pretty JSON, bulk status fixes.

### `inbox`
- One **Thread per Order**, **Message** entries (system/user/admin) with read tracking.
- Context processor exposes `inbox_unread_count` to draw an unread badge in the navbar.
- Signals create a system message on **confirmed payments**.

### `blog`
- Minimal `Post` with image, list/detail, admin with text/date filters and **“Clear image”** bulk action.

### `projects`
- `Project` with image and optional preview; compression signal/admin identical to `services`.
- Grid template with lazy previews.

### `users`
- Custom `User` (avatar upload + preset **avatar_choice**, `display_name`, `avatar_url`).
- Classic auth + **Pi Login** (`/users/pi/login/`) using Pi token → `/v2/me` → create/login user.
- Profile edit form, CV download protected (`/private/cv.pdf`).
- reCAPTCHA v3 mixin used in auth forms.
- Admin: actions (activate/deactivate/send reset), avatar thumb, orders count column.

### `core`
- Home with featured services, latest projects/posts, animated stats; legal pages.
- **Base template** with SEO, social OG/Twitter, canonical URLs, and cookie consent UI.
- Minimal service worker (`/sw.js`) and a `validation-key.txt` view for external verification.

---

## 🔄 Pi Payment Flow (SDK Integration)

On the **service detail** page, the button triggers JS (see `static/js/pi_payments.js`) that:

1. `POST /orders/checkout/<slug>/` → returns JSON with `{ memo, metadata, amount (π) }`.
2. Calls **Pi SDK** with that payload.
3. Pi SDK then pings your backend:
   - `POST /pi/approve/` → backend fetches `/v2/payments/<pid>` and links to our `Payment` by `metadata.order_number`.
   - `POST /pi/complete/` with `txid` → validates against snapshot and confirms.
   - `POST /pi/cancel/` if the user aborts or balance is insufficient.
4. (Optional) Pi **webhook** → reconciles statuses and preserves **idempotency**.

**Important**: snapshot at checkout stores `{ price_eur, eur_per_pi, amount_pi }` inside `Payment.raw_payload.pricing`. All later checks compare against this snapshot.

---

## 🛡️ Security & Hardening

- **django-axes**: brute‑force protection (lockout page wired at `errors/locked_out.html`).
- **reCAPTCHA v3**: validates `action` + `score` with configurable threshold.
- **CSP/COOP/COEP**: relaxed only in sandbox to allow iframe (Pi Browser) — locked down otherwise.
- **Strict cookies & HSTS** in production; **WhiteNoise** for static files with immutable caching.
- **Proxy aware** headers for Railway / tunnels; trusted origins required for CSRF.

---

## 🗃️ Database & Migrations

- Configure via `DATABASE_URL` (preferred) or individual engine keys.
- MySQL detection removes `sslmode` (not supported) and sets `utf8mb4` properly.
- `makemigrations` is already run for the included models. Apply with `migrate`.

---

## 🖼️ Media & Static

- `MEDIA_ROOT` defaults to `BASE_DIR/media` (or `/data/media` if `USE_VOLUME_MEDIA=true`).
- **WhiteNoise** serves static files; in prod it uses `CompressedManifestStaticFilesStorage` with **immutable cache** for hashed assets.

---

## 🧪 Testing Tips

- Switch `EMAIL_BACKEND` to console locally (already set) to verify password reset flows.
- For Pi flows without real wallet, run with `PI_SANDBOX=true` and simulate callbacks to `/pi/*` endpoints.
- Use **admin actions** in `pi_payments` to toggle statuses or **Sync from Pi** during debugging.

---

## 🔧 Admin (django‑unfold)

- Custom branding (logos, colors), dashboard shortcut to key models.
- List pages show **status badges**, **thumbnails**, pretty JSON, **row actions** (e.g., “Recompress”).

---

## 🔗 Routes Overview (selected)

- `/` Home · `core:home`
- `/blog/` · list/detail
- `/projects/` · list
- `/services/` · list/detail, `payment_success`
- `/orders/` · list/detail
- `/inbox/` · thread list/detail
- `/pi/approve|complete|cancel|webhook/` (server callbacks)
- `/users/login|register|profile|logout|cv|get/`
- `/validation-key.txt` (static key view)
- `/sw.js` (minimal SW)

---

## 🧰 Operations & Deployment Notes

- Set **`ALLOWED_HOSTS`** and **`CSRF_TRUSTED_ORIGINS`** precisely (schema required for CSRF, no trailing slash).
- Behind a proxy/CDN (Railway, Fly, Render), keep `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` enabled.
- Ensure **FFmpeg** exists in production image or layer.
- Disable `PI_SANDBOX` in real prod unless you explicitly support Pi Browser iframe.
- For object storage (S3/GCS), move video compression to an async worker and write back to the bucket.

---

## 📄 License

Choose your preferred license (e.g., **MIT**) and place it as `LICENSE` in the repo.

---

## 🙌 Credits

- Built by José Félix using **Django**, **Bootstrap**, **django‑unfold**, and the **Pi Network SDK**.
