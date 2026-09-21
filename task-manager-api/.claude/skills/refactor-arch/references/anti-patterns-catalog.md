# Anti-Patterns Catalog (Phase 2)

Each entry has: **severity rule**, **detection signals** (grep patterns + structural checks), **not a finding when** (false positives) and the **playbook transformation** that fixes it (`refactoring-playbook.md`).

Grep patterns are case-insensitive starting points (`grep -rniE '<pattern>' --include=*.py --include=*.js .`). Always confirm by reading the code.

## Severity scale (MVC / SOLID based)

| Severity | Definition |
|---|---|
| **CRITICAL** | Severe architecture or security flaws that prevent correct operation, expose sensitive data (e.g. hardcoded credentials, SQL injection) or completely violate separation of concerns (e.g. a "God Class" holding database, complex logic and routing in the same file). |
| **HIGH** | Strong violations of MVC or SOLID that make maintenance and testing very hard (e.g. heavy business logic inside controllers/routes, strong coupling without dependency injection, mutable global state across the app). |
| **MEDIUM** | Standardization problems, code duplication or moderate performance bottlenecks (e.g. N+1 queries, inadequate middleware usage, missing validation on routes). |
| **LOW** | Readability improvements, poor variable names, loose magic numbers. |

Escalation rules:
- A problem that is **exploitable remotely without authentication** is at least HIGH; if it leaks secrets/credentials, allows arbitrary queries or destroys data, it is CRITICAL.
- A problem that makes the app **crash (HTTP 500) on ordinary invalid input** is at least MEDIUM.
- A deprecated API that is **already removed** in the installed version (app breaks) is HIGH; merely deprecated is MEDIUM; style-only modernization is LOW.

## Index

| ID | Anti-pattern | Default severity | Playbook |
|---|---|---|---|
| AP-01 | Hardcoded credentials and secrets | CRITICAL | T-01 |
| AP-02 | SQL / query injection | CRITICAL | T-02 |
| AP-03 | God Class / God module (no separation of concerns) | CRITICAL | T-03 |
| AP-04 | Sensitive data exposure (responses and logs) | CRITICAL | T-05 |
| AP-05 | Insecure password storage | CRITICAL | T-04 |
| AP-06 | Unprotected destructive/debug endpoints and broken authentication | CRITICAL / HIGH | T-06 |
| AP-07 | Business logic in routes/controllers (fat controller) | HIGH | T-03, T-13 |
| AP-08 | Tight coupling without dependency injection / no composition root | HIGH | T-11 |
| AP-09 | Mutable global state | HIGH | T-11, T-18 |
| AP-10 | Insecure runtime configuration (debug mode, open bind, wildcard CORS) | HIGH | T-01 |
| AP-11 | Non-atomic multi-step writes (missing transaction) | HIGH | T-09 |
| AP-12 | Broken referential integrity on delete | HIGH | T-17 |
| AP-13 | N+1 queries and per-row aggregation | MEDIUM | T-08 |
| AP-14 | Missing or inconsistent input validation | MEDIUM | T-12 |
| AP-15 | Swallowed / generic exception handling, no centralized error handler | MEDIUM | T-07 |
| AP-16 | Duplicated code | MEDIUM | T-13 |
| AP-17 | Callback hell / pyramid of doom | MEDIUM | T-10 |
| AP-18 | Deprecated / obsolete APIs and dependencies | MEDIUM (see rules) | T-14 |
| AP-19 | Inadequate middleware usage / inconsistent responses | MEDIUM | T-07 |
| AP-20 | Magic numbers and strings | LOW | T-15 |
| AP-21 | Poor naming | LOW | T-15 |
| AP-22 | Dead code and unused imports/dependencies | LOW | T-16 |
| AP-23 | print/console logging instead of a logger | LOW | T-16 |
| AP-24 | Verbose / non-idiomatic conditionals | LOW | T-16 |

---

## AP-01 — Hardcoded credentials and secrets
**Severity:** CRITICAL (secrets, passwords, API/payment keys, signing keys in source). Non-secret config hardcoded (port, DB file name) is LOW → report under AP-20.

**Detection signals**
- `(secret|password|passwd|pwd|pass|api[_-]?key|token|private[_-]?key|credential)\w*["']?\s*[:=]\s*["'][^"']{3,}["']`
- `SECRET_KEY\s*[\]=:]` followed by a literal; `app.config\[["']SECRET_KEY["']\]\s*=\s*["']`
- Known key prefixes: `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `xox[bp]-`
- Config objects/dicts with literal credentials (`dbPassword`, `smtp_pass`, `mailPassword`, `gatewayKey`)
- SMTP/DB connection strings with user:password (`://\w+:[^@]+@`)

**Not a finding when:** the value comes from `os.environ`/`process.env` without a secret default, or it is a clearly fake placeholder in `.env.example`/tests.

**Evidence to report:** file:line of each literal; mention if the secret is also returned or logged (then also AP-04).

---

## AP-02 — SQL / query injection
**Severity:** CRITICAL.

**Detection signals**
- Python: `execute\(\s*f["']`, `execute\([^)]*["']\s*\+`, `execute\([^)]*%\s*\(`, `\.format\(` inside a query string, `text\(f["']`
- JS: `(run|get|all|query|exec)\(\s*` followed by a template literal containing `\$\{` or string concatenation with `+`
- Query strings built incrementally: `query \+= ["'] AND .*["'] \+`, `WHERE .*=\s*'["']\s*\+`
- `LIKE '%" + term + "%'`
- ORMs: `.raw(`, `sequelize.query(` with interpolation, `whereRaw(` with interpolation

**Not a finding when:** placeholders are used (`?`, `%s` passed as parameters, `:name`, `$1`) and only constant fragments are concatenated (e.g. `" AND categoria = ?"`).

**Evidence to report:** every function/line that builds SQL from input; mention the exploitable endpoint (e.g. login bypass, search).

---

## AP-03 — God Class / God module
**Severity:** CRITICAL when one class/file mixes **routing/HTTP + data access + business rules** (often also schema/seed/config). HIGH when it mixes two of them for several domains.

**Detection signals**
- A single class/module registers routes **and** runs SQL/ORM calls **and** computes business rules (`setupRoutes`/`add_url_rule` + `db.run`/`execute` + calculations).
- A file over ~250 lines, or a class with methods for 3+ unrelated domains (users, orders, payments, reports).
- Names like `*Manager`, `*Utils`, `*Helper`, `Main`, `Core`, `Server` that contain routes or SQL.
- Root `models.py` holding all queries **and** business rules for every entity; root `controllers.py` holding validation + notifications + formatting for every entity.
- Schema creation / seed data inside the same class that serves HTTP.

**Not a finding when:** a large file is only declarative (route table, schema definitions) with a single responsibility.

**Evidence to report:** `file:start-end` of the class/module and the list of responsibilities found.

---

## AP-04 — Sensitive data exposure (responses and logs)
**Severity:** CRITICAL when passwords, password hashes, secrets, tokens, card numbers or internal config are returned or logged; MEDIUM for PII (e-mails) in logs.

**Detection signals**
- Serializers returning password fields: `["']?(password|senha|pass|pwd|hash)["']?\s*:` inside `to_dict`/`toJSON`/response dicts.
- `SELECT \*` from a users table returned directly to the client.
- Health/debug endpoints returning `secret_key`, `debug`, `db_path`, env vars.
- Logs with sensitive values: `(print|console\.log|logger\.\w+)\(.*(card|cc|password|senha|token|key|secret)`.
- Exception text returned to clients (`str(e)`, `err.message`) — report under AP-15 unless it leaks secrets.

**Not a finding when:** the field is write-only (accepted in input but excluded from output) or logs mask the value (`****1234`).

---

## AP-05 — Insecure password storage
**Severity:** CRITICAL.

**Detection signals**
- Plaintext: password inserted as received (`INSERT INTO users ... password` with the raw value) or compared in SQL (`WHERE email = ? AND senha = ?`).
- Weak/fast hashes: `hashlib\.(md5|sha1|sha256)\(` or `createHash\(["'](md5|sha1|sha256)` used for passwords, no salt.
- Home-made "crypto": loops with `base64`, `substring`, string reversal, XOR.
- Default passwords assigned when missing (`password || "changeme"`).
- Very small minimum password length (< 8) — mention as part of the finding.

**Not a finding when:** `bcrypt`, `argon2`, `scrypt`, `pbkdf2` (with salt and iterations), `werkzeug.security.generate_password_hash`, `crypto.scrypt` are used.

---

## AP-06 — Unprotected destructive/debug endpoints and broken authentication
**Severity:** CRITICAL for endpoints that execute arbitrary SQL/commands, reset/drop data or expose admin data **without authentication**. HIGH for fake/predictable tokens, missing authorization on admin routes, or clients choosing their own role (privilege escalation).

**Detection signals**
- Route handlers receiving a query/command from the request: `request.*\[?["']sql["']`, `req\.body\.(sql|query|cmd)` then `execute(`/`exec(`.
- Routes under `/admin`, `/debug`, `/reset`, `/internal` with no auth decorator/middleware.
- `DELETE FROM` for every table inside a handler.
- Tokens built from predictable values (fixed prefix + user id, timestamps, base64 of the id): `token["']?\s*[:=].*\+\s*str\(|token.*\$\{.*id|b64encode\(.*id`.
- Role taken from the request body on self-registration (`role = data.get('role'`, `req.body.role`).

**Not a finding when:** a guard (decorator/middleware) validates a signed token/session and role before the handler runs.

**Phase 3 obligation:** the *privilege escalation* part of this finding (a `role`/`is_admin`/`permissions` field accepted from an anonymous client, on create or update) and the *predictable token* part must be fixed in Phase 3 — see `refactoring-playbook.md` T-06 and `mvc-guidelines.md` §9 exception 8. Only "every route is public and there is no authentication at all" may stay in "Remaining Items", and the report must say which part was fixed and which part was not.

---

## AP-07 — Business logic in routes/controllers (fat controller)
**Severity:** HIGH.

**Detection signals**
- Route/controller functions longer than ~30 lines containing calculations, status rules, aggregation loops, discount/stock/payment rules.
- ORM/SQL calls directly inside route handlers (`Model.query`, `db.session`, `cursor.execute`, `db.run`) — the route is doing the model's job.
- Side effects (e-mail, SMS, payment, notifications — even simulated with print/log) triggered inline in handlers.
- A `services/` folder that exists but is not imported by the routes.

**Not a finding when:** the handler only parses input, calls one model/service method and maps the result to a response.

---

## AP-08 — Tight coupling without dependency injection / no composition root
**Severity:** HIGH.

**Detection signals**
- Concrete dependencies created inside classes/functions: `new sqlite3.Database(` in a constructor, `NotificationService()` inside a handler, `smtplib.SMTP(` inside business code.
- Modules importing a global connection/app everywhere (`from database import get_db`, `from app import app`), making tests impossible without the real DB.
- No app factory: `app = Flask(__name__)` / `const app = express()` configured at import time, with side effects on import (`db.create_all()`, schema creation, `listen`).
- Scripts importing the running app module to reuse its globals (e.g. seed scripts doing `from app import app, db`).

**Not a finding when:** a `create_app()`/`createApp(deps)` factory wires dependencies and modules receive them as parameters.

---

## AP-09 — Mutable global state
**Severity:** HIGH.

**Detection signals**
- Python: `global \w+` inside functions; module-level `_cache = {}` / `connection = None` mutated at runtime; `sqlite3.connect(..., check_same_thread=False)` shared across requests.
- JS: module-level `let \w+ = \{\}|let \w+ = \[\]|let \w+ = 0` mutated by functions and exported (`module.exports = { globalCache, ... }`).
- In-memory lists acting as storage in service instances (grows forever, lost on restart, not shared across workers).

**Not a finding when:** the module-level value is immutable (constants, frozen config) or an intentionally process-wide, thread-safe resource created by the composition root (e.g. `db = SQLAlchemy()` extension object).

---

## AP-10 — Insecure runtime configuration
**Severity:** HIGH (`debug=True` in code, especially with `host="0.0.0.0"` — the interactive debugger allows code execution). MEDIUM for wildcard CORS on an API without auth needs.

**Detection signals**
- `app\.run\(.*debug\s*=\s*True`, `DEBUG["']?\]?\s*=\s*True`
- `host\s*=\s*["']0\.0\.0\.0["']` hardcoded
- `CORS\(app\)` without `origins`, `app\.use\(cors\(\)\)` without options
- Environment labels hardcoded (`"ambiente": "producao"` while debug is on)

**Not a finding when:** values come from configuration with safe defaults (`DEBUG` false unless env says otherwise).

---

## AP-11 — Non-atomic multi-step writes (missing transaction)
**Severity:** HIGH (partial writes / inconsistent data, race conditions such as overselling).

**Detection signals**
- Two or more `INSERT/UPDATE/DELETE` executed in sequence for one business operation without `BEGIN/COMMIT/ROLLBACK`, `with conn:`, `db.session.begin()`, `db.serialize` + transaction.
- Nested callbacks each performing an insert, returning 500 on the second failure without undoing the first.
- Read-check-write without locking/conditional update (`SELECT estoque` → compare → `UPDATE estoque = estoque - n`).
- `commit()` inside loops.

**Not a finding when:** a single statement, or the framework wraps the request in a transaction.

---

## AP-12 — Broken referential integrity on delete
**Severity:** HIGH when deleting a parent leaves orphan rows that corrupt other features (reports, listings); MEDIUM when orphans are harmless.

**Detection signals**
- `DELETE FROM <parent>` with child tables referencing it (`<parent>_id` columns) and no `ON DELETE CASCADE`, no manual cleanup, no transaction.
- Response text or comments admitting leftovers after the delete.
- ORM relationships without `cascade` while the delete handler manually loops over children (or forgets them).
- Error callback ignored on delete (`(err) => { res.send(...) }` without checking `err`).

---

## AP-13 — N+1 queries and per-row aggregation
**Severity:** MEDIUM.

**Detection signals**
- A query inside a loop over the result of another query: `for .* in .*:` followed by `execute(`/`.query.get(`/`.query.filter`; `forEach(` containing `db.get(`/`db.all(`.
- Lazy relationship access inside loops (`len(user.tasks)`, `task.user.name`) without `joinedload`/`selectinload`.
- Many separate `COUNT(*)` queries that could be one `GROUP BY`.
- Loading every row (`.all()`, `SELECT *`) to count or filter in application code.

**Not a finding when:** the loop is bounded by a small constant and documented, or data is batch-loaded (`IN (...)`, JOIN, eager loading).

---

## AP-14 — Missing or inconsistent input validation
**Severity:** MEDIUM (HIGH if it allows corrupting business data, e.g. negative quantities increasing stock).

**Detection signals**
- `request.get_json()` / `req.body` used without checking for `None`/non-object → `AttributeError`/`TypeError` → 500.
- Numeric comparisons on unvalidated input (`if preco < 0` where `preco` may be a string).
- Fields accepted without type/range checks (quantity, price, priority, dates, e-mail, color, booleans).
- The same entity validated differently on create vs update (e.g. category checked only on create).
- Lists of allowed values duplicated per route instead of a single validator.

---

## AP-15 — Swallowed / generic exception handling, no centralized error handler
**Severity:** MEDIUM.

**Detection signals**
- Python: `except:` (bare), `except Exception as e:` returning `str(e)` to the client, `except ...: pass`.
- JS: callbacks ignoring `err` (`(err, row) => {` without `if (err)`), empty `catch {}`, errors turned into plain text with inconsistent status.
- Every handler wrapped in its own try/except with identical code — no `@app.errorhandler` / Express error middleware `(err, req, res, next)`.

---

## AP-16 — Duplicated code
**Severity:** MEDIUM.

**Detection signals**
- Identical or near-identical blocks (≥ 5 lines) in two or more places: row-to-dict mappings, validation chains, "is overdue" rules, listing functions differing only by a WHERE clause.
- Helper/model methods that already implement the rule but are re-implemented inline (e.g. an entity method exists and routes copy its logic).
- The same literal list (`['pending', 'done', ...]`, roles, categories, regexes) in several files.

**How to confirm:** grep a distinctive line of the block (`grep -rn "status != 'done'"`), compare occurrences.

---

## AP-17 — Callback hell / pyramid of doom
**Severity:** MEDIUM.

**Detection signals**
- More than 3 nested callbacks (`=> {` / `function(err` indentation growing), manual counters to know when parallel callbacks finished (`pending--; if (pending === 0)`).
- `const self = this` to reach the outer scope inside nested callbacks.

**Not a finding when:** code uses `async/await` or promise composition (`Promise.all`).

---

## AP-18 — Deprecated / obsolete APIs and dependencies
**Severity:** MEDIUM by default; HIGH if removed in the installed version or security-relevant; LOW for style modernization only.

Report each deprecated API with the **modern replacement** (also fill the report's "Deprecated APIs" table).

| Stack | Deprecated / obsolete | Modern replacement | Status |
|---|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` | Deprecated since 3.12 |
| Python ≥ 3.12 | `sqlite3` default datetime adapters/converters | explicit adapters or ISO strings | Deprecated since 3.12 |
| Python | `distutils`, `imp`, `asynchat`, `asyncore`, `cgi`, `pipes` | `setuptools`/`packaging`, `importlib`, `asyncio`, `email`/`multipart`, `shlex` | Removed (3.12/3.13) |
| Python | `pkg_resources` | `importlib.metadata`, `importlib.resources` | Deprecated |
| SQLAlchemy 2.x | `Model.query.get(id)` / `session.query(Model).get(id)` | `db.session.get(Model, id)` | Legacy since 2.0 (`LegacyAPIWarning`) |
| SQLAlchemy 2.x / Flask-SQLAlchemy 3.x | `Model.query.filter_by(...).all()` (legacy Query API) | `db.session.execute(db.select(Model).filter_by(...)).scalars().all()` | Legacy (still works) — LOW unless mixed with `.get()` |
| Flask ≥ 2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.env`/`FLASK_ENV`, `flask._app_ctx_stack` | setup in `create_app()`, `app.json` provider, `--debug`/`FLASK_DEBUG`, `flask.g` | Removed in 2.3/3.0 |
| Flask 3.x | `flask.__version__` | `importlib.metadata.version("flask")` | Deprecated |
| Werkzeug ≥ 3 | `werkzeug.urls.url_quote`, `url_parse` | `urllib.parse` | Removed |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` | Deprecated (DEP0005) |
| Node.js | `url.parse()` | `new URL()` | Deprecated (DEP0169) |
| Node.js | `crypto.createCipher()` | `crypto.createCipheriv()` | Removed |
| Node.js | `fs.exists()` | `fs.existsSync()` / `fs.promises.access()` | Deprecated |
| Node.js | `util.isArray()` and other `util.is*` helpers | `Array.isArray()`, `typeof` / `instanceof` checks | Deprecated (most `util.is*` removed in Node 23) |
| Express 4 → 5 | `req.param()`, `res.send(status)`, `res.json(obj, status)`, `app.del()`, `res.sendfile()` | `req.params/query/body`, `res.sendStatus()`, `res.status(s).json(obj)`, `app.delete()`, `res.sendFile()` | Removed in Express 5 |
| Express | `body-parser` package for JSON | `express.json()` / `express.urlencoded()` | Built-in since 4.16 |
| npm / Node modules | `request`, `node-uuid` packages; `domain` module; `querystring` module | `fetch`/`undici`, `crypto.randomUUID()`, `AsyncLocalStorage`, `URLSearchParams` | Deprecated (`querystring`: legacy) |
| Any | Dependencies flagged as deprecated/vulnerable by the package manager (`npm install` deprecation warnings, `npm audit --package-lock-only`, `pip-audit`) | Upgrade to the maintained version (prefer non-breaking) | Evidence from tool output |
| JS style | `var` declarations, callback-only DB drivers | `const`/`let`, promise-based wrappers | LOW |

**Detection signals:** grep each left-column API (`utcnow\(`, `\.query\.get\(`, `new Buffer\(`, `url\.parse\(`, `req\.param\(`, `before_first_request`, `body-parser`). Check the manifest versions first — only report what applies to the detected versions. For lockfiles, read `"deprecated":` entries in `package-lock.json`.

**Dependency audit (mandatory, read-only — never install anything in Phase 2):**

| Ecosystem | Command / source | What to report |
|---|---|---|
| npm | `npm audit --package-lock-only` (add `--json` for details); `grep -n '"deprecated"' package-lock.json` | Vulnerable packages with severity and fixed version; deprecated packages and which direct dependency pulls them |
| Python (`requirements.txt` with pins) | For each `name==version`: `curl -s https://pypi.org/pypi/<name>/<version>/json` and read the `vulnerabilities` array (`aliases`, `fixed_in`). `pip-audit -r requirements.txt` is an alternative when already installed | Vulnerable pins with CVE ids and the first fixed version; unpinned packages as a reproducibility note |
| Others | `go list -m -u all` / `govulncheck`, `bundle audit`, `composer audit`, `dotnet list package --vulnerable` | Same |

Severity: HIGH when the vulnerable package is used at runtime by the application (e.g. web framework, CORS middleware) and a fixed version exists; MEDIUM for build-time/transitive-only or unused packages; mention unused-but-declared dependencies under AP-22 too.

---

## AP-19 — Inadequate middleware usage / inconsistent responses
**Severity:** MEDIUM.

**Detection signals**
- Cross-cutting concerns repeated in every handler instead of middleware: auth checks, try/catch, logging, JSON parsing.
- Error responses mixing plain text (`res.send("Erro DB")`) and JSON, or different envelopes per route.
- Middlewares registered in the wrong order (error handler before routes, body parser after routes) or missing (`express.json()` absent while `req.body` is used).
- Global CORS without restriction (see also AP-10).

---

## AP-20 — Magic numbers and strings
**Severity:** LOW.

**Detection signals**
- Numeric literals other than `0`, `1`, `-1` in business logic: thresholds (`> 10000`, `* 0.1`), limits (`len(x) > 200`), ranges (`1..5`), iteration counts, days (`timedelta(days=7)`), ports.
- Status/role/category string literals repeated across files (`'pending'`, `'PAID'`, `'admin'`).

**Not a finding when:** the literal is defined once as a named constant or config value.

---

## AP-21 — Poor naming
**Severity:** LOW (MEDIUM if it causes bugs, e.g. shadowing builtins used later).

**Detection signals**
- 1–3 letter variables outside short loops/lambdas: `\b(let|const|var)\s+[a-z]{1,3}\s*=`, Python `^\s+[a-z]{1,2}\s*=`
- Cryptic abbreviations (`nm`, `ml`, `qt`, `tmp2`, `d`, `t`, `u`), generic names (`data`, `result`, `manager`, `utils`, `process`).
- Shadowing builtins (`id`, `type`, `list`, `filter`) as variables/parameters.
- Mixed languages for the same concept.

**Note:** request/response field names are part of the public contract — rename only internally (map at the controller boundary).

---

## AP-22 — Dead code and unused imports/dependencies
**Severity:** LOW.

**Detection signals**
- Imports never referenced: for each imported name, `grep -c "\bname\b" file` equals 1.
- Functions/classes/services never called anywhere (`grep -rn "function_name" .` returns only the definition).
- Exported variables never imported; config entries never read.
- Declared dependencies never imported (manifest vs grep).

---

## AP-23 — print/console logging instead of a logger
**Severity:** LOW (escalate to AP-04 if the message contains sensitive data).

**Detection signals**
- `print\(` in application code (outside CLI scripts), `console\.log\(` in request handlers; fake side effects implemented as prints ("SENDING EMAIL").
- No log levels, no logger configuration.

---

## AP-24 — Verbose / non-idiomatic conditionals
**Severity:** LOW.

**Detection signals**
- `if cond: return True else: return False` / `if (cond) { return true } else { return false }`
- Nested `if` pyramids 3+ levels deep for a single boolean rule.
- `type(x) == list` instead of `isinstance`; `== None` instead of `is None`; `len(x) == 0` checks after `not x`.
