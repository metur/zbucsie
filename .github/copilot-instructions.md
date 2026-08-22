# Copilot Instructions

## Commands

- Install dependencies: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- Run locally: `.\.venv\Scripts\python.exe main.py`
- The deployment entry point is `gunicorn main:app` (`Procfile`).
- There is no committed test suite, test runner configuration, or linter configuration. Do not claim a full-suite or single-test command exists. For a syntax-only check of a changed module, use `.\.venv\Scripts\python.exe -m py_compile <module>.py`.

## Architecture

- `main.py` owns the Flask application, configuration, routes, CSRF setup, SQLite initialization, and the APScheduler lifecycle. The database is `instance\users.db`, configured through the relative URI `sqlite:///users.db`; tables are created at application startup.
- `extensions.py` exports the shared, unbound Flask-SQLAlchemy `db` instance. Import this instance in models and routes; initialize it only through `db.init_app(app)` in `main.py`.
- `player.py` defines the persistent `User` and one-to-one `Player` models. A `Player` records score, workers, chosen camp, and whether that camp is built. User authentication is session-based: `session['user_id']` identifies the active user.
- Jinja templates are server-rendered from `templates\`. `base.html` supplies the shared layout and CSRF token meta tag. `dashboard.html` keeps its score and worker counts in JavaScript and calls the JSON endpoints for score increments, worker purchases, and camp construction. Camp art resides in `static\`.

## Project-specific behavior and conventions

- Keep all state-changing browser requests CSRF-protected. Flask-WTF forms render `form.hidden_tag()`, while JavaScript `fetch` calls send the token from `meta[name="csrf-token"]` as `X-CSRFToken`.
- Routes that require an account check `session.get('user_id')`; preserve the current response style: page routes redirect to `home`, while JSON game-action endpoints return a JSON error and an HTTP status.
- A player is created during registration and may also be created defensively on login or dashboard access. Preserve this lazy-creation behavior when handling legacy or incomplete records.
- Scoring is intentionally updated in two paths: APScheduler increments every player with a selected camp once per second by `1 + workers`, and the dashboard posts to `/increment_score` for client-side ticks and manual clicks. Changes to scoring, worker costs, or camp costs must keep `main.py` and the values rendered into `dashboard.html` consistent.
- Camps use the stable internal identifiers `stary`, `nowy`, and `bagno`. Those identifiers are stored in the database and derive both static asset names (`<camp>.png` and `<camp>_gray.png`) and the corresponding Polish display text.
- User-facing template copy and form labels are in Polish; keep new UI text in Polish and continue extending the `base.html` template blocks rather than introducing a separate layout.
