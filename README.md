# JFGC Dev — Full-Stack Portfolio & Services Platform

**A Django-powered professional portfolio and services platform** combining project showcases, a blog, service listings, customer orders, an order-linked inbox, and Pi Network SDK integration.

**Release:** `v1.0.0` (intended first stable release; publish the tag/release after final acceptance testing)  
**Stack:** Python · Django · Bootstrap · JavaScript · django-unfold · Pi Network SDK · Railway

> **Integration status:** The application has successfully started on Railway, including the `users.0002_user_pi_uid` migration and static-file collection. This does **not** by itself verify live Pi payments, all authenticated routes inside Pi Browser, or production login. Validate these flows before describing them as fully operational.

## ✨ Features

- **Professional portfolio:** project gallery, individual project pages, blog, and responsive presentation.
- **Service catalog:** detailed services with features, FAQs, images, and optional video previews.
- **Orders and checkout:** EUR-denominated orders with configurable EUR-to-π price conversion and checkout-time pricing snapshots.
- **Pi Network integration:** Pi SDK authentication, server-side token verification, payment lifecycle endpoints, and configurable Sandbox mode.
- **Customer inbox:** per-order threads for customer, administrator, and system messages, including unread indicators.
- **Administration:** customized `django-unfold` dashboard with status indicators, filters, thumbnails, and operational actions.
- **Security and delivery:** Django Axes, reCAPTCHA for applicable authentication flows, production cookie/HTTPS settings, WhiteNoise, SEO metadata, and a lightweight PWA service worker.

## 🏗️ Application Structure

```text
core/           Homepage, legal pages, shared templates, Pi iframe middleware
blog/           Blog posts, listing/detail pages, administration
projects/       Portfolio projects and media previews
services/       Service catalog, features, FAQs, service detail pages
orders/         Orders, order items, checkout, customer order views
pi_payments/    Payment records, SDK callback endpoints, reconciliation tools
inbox/          Per-order threads, messages, unread counts
users/          Custom user, Pi UID, authentication, profile, CV download
portfolio/      Django settings, URL configuration, WSGI
static/js/      Frontend JavaScript, including Pi SDK initialization and flows
```

## 🔐 Authentication and Pi Network

The platform supports Django authentication functionality and a configurable **Pi-only login experience**. When `PI_ONLY_LOGIN=True`, the login interface prioritizes Pi authentication rather than the traditional login form.

The Pi login flow uses the SDK in the browser, submits an access token to the Django endpoint `/users/pi/login/`, and verifies the token on the server before authenticating the associated user. The custom user model includes `pi_uid`, introduced through migration `users.0002_user_pi_uid`.

`PI_ACCOUNT_MIGRATION_LOCK` is a deployment control for the account migration/login policy. Review the associated backend logic before changing it, particularly when existing accounts must be preserved.

### SDK initialization

- `static/js/pi_payments/pi-init.js` initializes the Pi SDK and reads the Sandbox setting exposed by Django.
- `static/js/users/pi-login.js` handles the frontend login interaction.
- `core.context_processors.pi_settings` makes `PI_SANDBOX` available to templates.
- **Sandbox:** use `PI_SANDBOX=True` with the registered Pi Sandbox application context.
- **Production:** use `PI_SANDBOX=False` for the live Pi environment, subject to registration and real-device validation.

Opening a development tunnel directly inside Pi Browser is **not equivalent** to launching the registered Pi application. SDK authorization may depend on the registered app context.

## 💳 Orders and Pi Payments

The implemented payment workflow is designed around server-side checks and persisted pricing snapshots:

1. A customer selects a service and starts checkout.
2. Django creates the order/payment records and calculates the π amount using `PI_EUR_PER_PI`.
3. The frontend starts the payment through the Pi SDK.
4. Backend callbacks handle approval, completion, cancellation, and optional reconciliation.
5. The backend verifies payment details and updates the relevant payment/order state according to the implemented state machine.
6. Confirmed payments can generate system messages in the order inbox.

### Payment endpoints

```text
/pi/approve/
/pi/complete/
/pi/cancel/
/pi/webhook/
```

The integration is designed to associate payments with orders using metadata, validate amounts against checkout snapshots, and avoid duplicate state transitions. **Live Mainnet settlement, callback delivery, and full end-to-end payment behavior still require production verification.**

Relevant frontend files:

```text
static/js/pi_payments/pi-init.js
static/js/pi_payments/pi_payments.js
```

## 🛡️ Pi Browser Embedding and Security Headers

`core.middleware.PiSandboxHeadersMiddleware` is controlled by **`PI_BROWSER_EMBED_ENABLED`**, not by `PI_SANDBOX` or `DEBUG`.

When enabled, it allows embedding from configured Pi-related origins for selected routes:

```text
Public:  /, /users/login/, /blog/, /projects/, /services/
Private: /orders/, /inbox/, /users/profile/
```

For allowed paths, the middleware removes `X-Frame-Options` from the response and sets a restricted Content Security Policy `frame-ancestors` directive. Other paths receive `X-Frame-Options: DENY` and `frame-ancestors 'none'`.

**Important:** iframe permissions do not bypass authentication or authorization. Protected pages must still enforce normal Django access controls. Check actual URL patterns when adding new authenticated views; only the listed paths/prefixes are covered by this middleware implementation.

Do not confuse the two settings:

| Setting | Purpose |
| --- | --- |
| `PI_SANDBOX` | Selects Sandbox behavior for the Pi SDK integration. |
| `PI_BROWSER_EMBED_ENABLED` | Enables route-specific iframe response-header handling. |
| `PI_ONLY_LOGIN` | Configures the Pi-focused login experience. |
| `PI_ACCOUNT_MIGRATION_LOCK` | Controls the account migration/login restriction implemented in the backend. |

Additional security controls include Django Axes, CSRF protection, configurable secure cookies and HSTS, and reCAPTCHA on applicable non-Pi authentication forms.

## ⚙️ Requirements

- Python **3.12** is used in the current Railway build; use a compatible local Python version.
- Django and all dependencies from `requirements.txt` (consult the file for exact versions).
- A configured database supported by the project's settings (PostgreSQL or MySQL, as applicable).
- FFmpeg for video-preview compression features.
- A registered Pi application and appropriate credentials for Pi integration testing.

## 🚀 Local Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Create a local `.env` with the settings required by your deployment. Do not commit `.env`, API keys, database credentials, or other secrets.

## 🔧 Environment Variables

The following is an **illustrative configuration**, not a complete production `.env`. Confirm variable names against `portfolio/settings.py` before deployment.

```dotenv
# Django
DEBUG=True
SECRET_KEY=replace-with-a-local-development-secret
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Database (example only)
DATABASE_URL=postgres://user:password@localhost:5432/portfolio

# Media processing
USE_VOLUME_MEDIA=False
FFMPEG_CMD=ffmpeg

# Pi Network — local Sandbox example
PI_API_KEY=replace-with-your-server-api-key
PI_SANDBOX=True
PI_EUR_PER_PI=0.07753
PI_ONLY_LOGIN=True
PI_BROWSER_EMBED_ENABLED=True
PI_ACCOUNT_MIGRATION_LOCK=True

# reCAPTCHA (if applicable to enabled forms)
RECAPTCHA_SITE_KEY=replace-with-site-key
RECAPTCHA_SECRET_KEY=replace-with-secret-key
RECAPTCHA_MIN_SCORE=0.5
```

`PI_EUR_PER_PI` is a **manually configured application pricing input**, not a live market exchange-rate feed. `0.07753` reflects a recent project configuration and should be reviewed before accepting real payments.

For a live Pi environment, configure `PI_SANDBOX=False`. Only enable iframe embedding where required by the actual Pi Browser integration, and test login, navigation, cookies, and payment callbacks in that environment.

## 📦 Media, Static Files, and PWA

- WhiteNoise serves collected static assets in production.
- Django's `collectstatic` runs during deployment startup.
- The project includes a lightweight service worker and SEO/social metadata.
- Project/service MP4 previews may be compressed using FFmpeg. Confirm FFmpeg availability and persistent media storage in the deployment environment.
- If moving to object storage, consider asynchronous media processing instead of relying on filesystem-based signals.

## 🧪 Verification Checklist

Before announcing a release as fully validated:

- [ ] `python manage.py check` completes successfully.
- [ ] `python manage.py makemigrations --check --dry-run` reports no unexpected model changes.
- [ ] JavaScript files pass syntax checks (`node --check`).
- [ ] Railway deployment is healthy and the homepage loads over HTTPS.
- [ ] Project, blog, and service pages work in a regular browser.
- [ ] Pi login works in the **registered** Sandbox app and the intended live Pi environment.
- [ ] Orders, inbox, and profile views load inside the supported Pi Browser context.
- [ ] Payment approval, completion, cancellation, and duplicate callbacks are tested end-to-end.
- [ ] Production secrets, CSRF origins, cookies, and iframe headers have been reviewed.

### Latest confirmed deployment checks

The deployment logs shared during preparation showed:

- `users.0002_user_pi_uid` applied successfully.
- Static assets collected and post-processed.
- Gunicorn 23.0.0 started and bound to the configured port.

These are **startup checks**, not evidence that every user flow or live Pi transaction has passed acceptance testing.

## 🌐 Selected Routes

```text
/                   Homepage
/blog/              Blog
/projects/          Portfolio projects
/services/          Service catalog
/orders/            Customer orders
/inbox/             Customer messaging
/users/login/       Login
/users/pi/login/    Pi authentication endpoint
/users/profile/     User profile
/pi/approve/        Payment approval callback
/pi/complete/       Payment completion callback
/pi/cancel/         Payment cancellation callback
/pi/webhook/        Optional payment reconciliation endpoint
/sw.js              Service worker
```

Routes and permissions are subject to the active Django URL configuration.

## 🚢 Deployment

The project is deployed through **Railway** with GitHub-connected deployment, dependency installation, database migrations, static-file collection, and Gunicorn.

Typical application startup:

```bash
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput && \
gunicorn portfolio.wsgi:application --bind 0.0.0.0:$PORT
```

Review the configured branch and commit in Railway when diagnosing deployments. A previous deployment's logs may not represent the code currently on GitHub.

## 🗺️ Release Status and Roadmap

**`v1.0.0`** is the intended first stable release following `v1.0.0-rc.1` and `v1.0.0-rc.2`.

Near-term verification priorities:

1. Confirm production Pi Browser authentication in the registered app.
2. Test order details, inbox, and other protected pages in Pi Browser.
3. Complete live Pi payment acceptance testing, including reconciliation and retries.
4. Add automated tests around iframe security policies and payment state transitions.

## 👨‍💻 Author

**José Félix** — Full-Stack Developer & Product Builder  
GitHub: [@AmeriK88](https://github.com/AmeriK88)

## 📄 License

No license is declared in this README. Consult the repository for a `LICENSE` file and its terms before reusing or distributing the code. If you intend to open-source the project, add a license that reflects your preferred permissions.
