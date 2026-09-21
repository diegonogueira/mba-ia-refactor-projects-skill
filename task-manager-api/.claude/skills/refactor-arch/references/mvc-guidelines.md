# MVC Architecture Guidelines (Phase 3 target)

The target is a pragmatic MVC for HTTP APIs: **Models** own data and domain rules, **Views** own the HTTP surface (routes and response representation), **Controllers** own the request flow. Supporting modules (config, middlewares, services) keep each layer focused.

## Table of contents
1. Layer responsibilities
2. Dependency rules
3. Target layout — Python / Flask
4. Target layout — Node.js / Express
5. Mapping for other frameworks
6. Composition root and entry point
7. Configuration
8. Error handling
9. Contract preservation (and allowed exceptions)
10. Adapting to the starting point
11. Dependencies and tooling
12. Definition of done

---

## 1. Layer responsibilities

| Layer | MUST | MUST NOT |
|---|---|---|
| **Model** (`models/`) | Entities; data access with parameterized queries or ORM; transactions; domain rules that depend only on the entity's data (e.g. `is_overdue()`, `can_cancel()`, stock check/decrement); DB connection/session management (`models/database.*`) | Import the web framework request/response objects; build HTTP responses; read env vars directly (receive config) |
| **View** (`views/`) | Route table: URL + method → controller function (Flask Blueprint / Express Router); response presenters/serializers with an **allowlist** of public fields | Contain SQL/ORM calls, business rules or validation logic |
| **Controller** (`controllers/`) | Read request data (body, params, query); call validators; call model/service methods; translate results/errors into status codes and views; keep each action short (≈ 5–25 lines) | Run SQL/ORM queries directly; contain business calculations; send e-mails/payments inline; catch-all `try/except` that returns `str(e)` |
| **Service** (`services/`, optional) | Use cases that coordinate **several models** or **external side effects** (place order = customer + stock + payment + audit log; notifications; payment gateway) | Know about HTTP (request/response objects, status codes) |
| **Middleware** (`middlewares/`) | Centralized error handling; cross-cutting guards (admin token, auth), request logging | Business rules |
| **Config** (`config/`) | Read environment variables once, validate, expose typed settings with safe defaults | Contain real secrets as defaults |
| **Utils** (`utils/`, optional) | Pure helpers and shared constants/validators without framework or DB imports | Become a new God module; hold state |

Rule of thumb for "where does this line go?":
1. Does it touch the database? → Model.
2. Is it a rule of the business that would stay the same in a CLI version of the app? → Model (single entity) or Service (several entities / side effects).
3. Does it read the request or pick a status code? → Controller.
4. Does it declare a URL or shape the JSON? → View.

## 2. Dependency rules

```
routes (views/*_routes) → controllers → services → models → database
                              │    \________________↗ (controllers may call models directly when no service is needed)
                              └──→ presenters (views/serializers)  — the controller selects/renders the view
middlewares, config, utils: may be imported by any layer; they import no layer above them
```

- Imports point **downwards**. Models and services never import controllers, routes or presenters; services never import controllers.
- Controllers may import the View layer's **presenters/serializers** (choosing and rendering the view is the controller's job in MVC), but never the route modules. Presenters import nothing above models.
- The composition root (`app.py` / `app.js`) is the only module that knows every layer and wires them.
- Pass dependencies (db handle, settings, services) as parameters/constructor arguments or via the framework's app context — not by importing mutable globals.

## 3. Target layout — Python / Flask

```
<project>/
├── app.py                          # thin entry point: from src.app import create_app; app.run(...) — keeps `python app.py` working
├── requirements.txt
├── .env.example                    # documented env vars, fake values only
├── README.md                       # updated run instructions
└── src/
    ├── __init__.py
    ├── app.py                      # composition root: create_app(config) registers extensions, blueprints, error handlers
    ├── config/
    │   ├── __init__.py
    │   └── settings.py             # Settings loaded from os.environ with safe defaults
    ├── models/
    │   ├── __init__.py
    │   ├── database.py             # connection/session factory, schema bootstrap, seed helpers
    │   └── <entity>_model.py       # one module per entity/aggregate
    ├── services/                   # optional
    │   └── <use_case>_service.py
    ├── controllers/
    │   ├── __init__.py
    │   └── <domain>_controller.py
    ├── views/
    │   ├── __init__.py
    │   ├── <domain>_routes.py      # Blueprint: only url → controller bindings
    │   └── serializers.py          # optional: entity → dict with public fields
    ├── middlewares/
    │   ├── __init__.py
    │   └── error_handler.py        # register_error_handlers(app); AppError hierarchy
    └── utils/                      # optional: validators.py, constants.py
```

Flask specifics:
- `create_app()` builds the app; nothing runs at import time except definitions.
- Blueprints live in `views/`; the handler functions they bind live in `controllers/`.
- Use `app.config.from_mapping(settings)`; access settings via `current_app.config` or explicit parameters.
- Raw `sqlite3`: open a connection per request (`flask.g`) or per operation, close it in `teardown_appcontext`; enable `PRAGMA foreign_keys = ON`.
- Flask-SQLAlchemy: `db = SQLAlchemy()` in `models/database.py`; `db.init_app(app)` in `create_app()`; use `db.session.get(Model, id)` and `db.select(...)`.
- Scripts such as `seed.py` must import `create_app()` instead of a module-level app.

## 4. Target layout — Node.js / Express

```
<project>/
├── package.json                    # "start" keeps working (update the path if the entry file moves)
├── .env.example
├── README.md
└── src/
    ├── app.js                      # entry point: loads settings, builds the app via createApp(), calls listen()
    ├── createApp.js                # composition root (optional split): wires db, models, services, controllers, routes, middlewares
    ├── config/
    │   └── settings.js             # reads process.env with safe defaults
    ├── models/
    │   ├── database.js             # connection, promise helpers (run/get/all), schema + seed, transaction helper
    │   └── <entity>Model.js
    ├── services/
    │   └── <useCase>Service.js
    ├── controllers/
    │   └── <domain>Controller.js
    ├── views/
    │   ├── routes.js               # express.Router(): url → controller bindings
    │   └── serializers.js          # optional presenters
    ├── middlewares/
    │   ├── errorHandler.js         # (err, req, res, next) + notFound
    │   └── asyncHandler.js         # wraps async controllers so rejections reach the error handler
    └── utils/
```

Express specifics:
- Build the app in a function that receives dependencies (`createApp({ db, settings })`) — `listen()` happens only in the entry point.
- Promisify callback drivers once in `models/database.js`; the rest of the code uses `async/await`.
- Register in this order: body parsers → routes → 404 handler → error handler.
- Keep CommonJS vs ESM consistent with the original project.

## 5. Mapping for other frameworks

| Framework | Model | View | Controller |
|---|---|---|---|
| FastAPI | `models/` (SQLAlchemy/Pydantic entities + repositories) | `views/` routers + response schemas | `controllers/` functions called by routers |
| Django / DRF | `models.py` per app | `urls.py` + serializers/templates | views (Django "views" are controllers) — keep business rules in models/services |
| NestJS | entities/repositories | controllers' route decorators + DTOs | providers/services orchestrating |
| Spring Boot | `@Entity` + repositories | `@RestController` mappings + DTOs | `@Service` classes |
| Rails / Laravel | ActiveRecord / Eloquent models | routes + views/serializers | controllers (thin) + service objects |

Follow the framework's own conventions when they already implement MVC; the goal is responsibilities, not folder names.

## 6. Composition root and entry point

- Exactly **one** place creates the app and wires dependencies (`create_app` / `createApp`).
- The **original start command must keep working** (`python app.py`, `npm start`, etc.). Either keep a thin entry file at the original path or update `package.json`/README consistently.
- Port and host come from config with the same defaults as before (same port as the original).
- Schema bootstrap and seed run from the composition root or a dedicated script — not as an import side effect of a model.

## 7. Configuration

- All settings in `config/settings.*`, read from environment variables.
- Non-secret values keep their original defaults (port, DB path/URI, feature flags).
- Secrets (`SECRET_KEY`, API keys, SMTP/DB passwords) have **no real default**: if the variable is missing, generate an ephemeral random value for development (e.g. `secrets.token_hex(32)`, `crypto.randomBytes(32)`) and log a warning, or leave the integration disabled.
- `DEBUG` defaults to `false`; enable via env var.
- `HOST` defaults to `127.0.0.1` (bind to all interfaces only when `HOST=0.0.0.0` is set explicitly, e.g. in containers); report the new default under "Contract Changes". Keep the original port as default.
- CORS origins configurable (default: allow all only if the original did, but through config).
- Add `.env.example` with every variable and fake values; never commit a real `.env`. If nothing loads `.env` automatically, say so in the file (e.g. "export these variables") instead of "copy to .env".
- Write comments and docs you create (README updates, `.env.example`, docstrings) in the same language as the project's existing documentation.

## 8. Error handling

- Define an application error hierarchy (`AppError(status, message)`, `ValidationError` 400, `NotFoundError` 404, `ConflictError` 409, `ForbiddenError` 403).
- Controllers/services raise/throw these errors; the **central handler** converts them to the project's existing error envelope (e.g. `{"erro": msg}` or `{"error": msg}`) and status.
- Unexpected exceptions → log the stack server-side, return a generic 500 message (no `str(e)`).
- Invalid JSON / wrong content type → 400, not 500.

## 9. Contract preservation (and allowed exceptions)

Keep unchanged:
- Every route path and HTTP method from the Phase 1 inventory.
- Request field names (even cryptic ones — rename only internally, mapping at the controller).
- Success status codes and response envelopes/field names (`{"dados": ..., "sucesso": true}` stays as is).
- Error status codes for the cases the original handled (400/401/404/409), and their message texts when reasonable.
- Port and start command.
- Response **headers** the original framework sent (e.g. `Allow` on 405, `Content-Type`, CORS headers). Converting an HTML error page into JSON must copy the original headers — dropping them is a regression, not a contract exception.

Allowed exceptions (each must be listed under "Contract Changes" in the Phase 3 output):
1. **Remove sensitive fields** from responses (passwords, hashes, secret keys, internal config).
2. **Destructive / admin-data endpoints that had no authentication** (arbitrary SQL, database reset, delete-anything, reports with other people's personal or financial data): keep the route registered but **closed by default**. The guard denies (403 with the project's error envelope) unless an explicit config flag **and** a token are set; compare tokens with `hmac.compare_digest` / `crypto.timingSafeEqual`.
   - A guard that **stays open when the variable is unset** ("opt-in protection") does **not** close a CRITICAL/HIGH finding — the default has to be the safe one. Apply the same pattern in every project you touch, so the behaviour does not depend on which run produced the code.
   - Arbitrary SQL, if the route is kept at all, must be restricted to a single read-only `SELECT` **and** must not be able to read credential columns (password/hash/token): filter them out or reject the query. Removing the route is preferable when the Phase 2 recommendation said so.
3. **Inputs that crashed with 500** now return 400 with a validation message.
4. **Unexpected errors** return a generic message instead of exception text.
5. **Integrity fixes**: e.g. deleting a parent also removes/handles dependent rows inside a transaction; success message may change to reflect the real behavior.
6. **Business-rule bugs that corrupt data** (negative quantities, overselling) are rejected with 400.
7. **Credential format**: stored password hashes change algorithm; plaintext/legacy seed passwords must still authenticate after the change (re-hash seeds, or verify legacy hashes and upgrade on login).
8. **Secrets in logs and seeds**: stop logging values that may carry credentials (disable driver/ORM parameter echoing — e.g. `SQLALCHEMY_ENGINE_OPTIONS = {"hide_parameters": True}` — or log only the exception type/message), and stop seeding privileged accounts with well-known passwords (read them from the environment, or generate a random one at first boot and log it once).
9. **Privilege escalation**: a field that grants privileges (`role`, `is_admin`, `type`, `permissions`, `plan`, `scopes`) must stop being honoured when it comes from an **unauthenticated** client. Ignore it and use the least-privileged default, or reject the privileged value with the project's error envelope (400/403); the route, the method and the success status stay the same. **This is a required security fix, not a product decision** — it does not need authentication to exist, it only needs the endpoint to stop granting privileges to anonymous callers. The same applies to update endpoints: without a guard that proves who is calling, a public endpoint may not change a privilege field.

Not allowed without asking the user: adding mandatory authentication to endpoints that were public (i.e. turning a 200 into a 401 for a legitimate request), renaming routes/fields, changing ports, changing response envelopes. Report these as "Remaining Items" recommendations instead.

**Do not hide a fixable problem behind a bigger one.** "This needs authentication" only covers the part that really needs authentication. When a finding has a portion that can be fixed within the exceptions above (e.g. the privilege field of exception 9, a predictable token that can be signed, a missing ownership check that can become a 404), fix that portion now and keep only the genuinely blocked part in "Remaining Items", saying explicitly what was fixed and what was not.

## 10. Adapting to the starting point

| Starting point | Strategy |
|---|---|
| Single God class / file | Extract by responsibility and by domain: config → database → one model per table → services for multi-entity flows → controllers per route group → routes → error middleware → composition root. Delete the God class when empty. |
| Flat root modules named like layers (`models.py`, `controllers.py`, `database.py`) | Split per domain into the canonical folders; move SQL out of routes in the entry file; move business rules out of controllers; delete the flat files after migration. |
| Partially layered (`models/`, `routes/`, `services/`, `utils/` exist) | Keep entities and useful helpers (move under `src/`); convert `routes/` into `views/` (bindings only) + `controllers/` (flow); move queries/rules from routes into models/services; wire the unused service or delete it; centralize config and error handling; remove duplicated rules by reusing model methods. |
| Already MVC | Only fix the audit findings in place. |

When moving a module, update every import and remove the old file — no duplicate copies left behind.

## 11. Dependencies and tooling

- Do not swap the framework, database engine or data-access style (raw SQL stays raw SQL with placeholders; ORM stays ORM).
- Prefer the standard library or packages the framework already ships with (e.g. `werkzeug.security`, `itsdangerous`, Node `crypto`) over new dependencies.
- Upgrade a dependency only when needed to remove a deprecated/removed API or a known vulnerability with a compatible fix; record it.
- Keep `node_modules/`, virtualenvs, `*.db` and `.env` out of version control.

## 12. Definition of done

- [ ] Directory structure follows the layout above (models, views, controllers + config, middlewares).
- [ ] Configuration extracted to a config module; no hardcoded secrets.
- [ ] Models abstract all data access (no SQL/ORM calls in controllers or views).
- [ ] Views/routes only bind URLs to controllers (and serialize output).
- [ ] Controllers concentrate the request flow and stay thin.
- [ ] Error handling centralized.
- [ ] Single, clear entry point / composition root; original start command works.
- [ ] Application boots without errors.
- [ ] Every original endpoint responds as in the baseline (except documented contract changes).
- [ ] Re-audit shows no remaining CRITICAL/HIGH findings (or they are justified in "Remaining Items").
