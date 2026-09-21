# Refactoring Playbook (Phase 3)

Concrete transformations, each mapped to catalog entries. Examples show Python/Flask and Node.js/Express; apply the same idea to other stacks using the framework's idioms. Examples are illustrative — adapt names, envelopes and messages to the project so the public contract is preserved.

## Index

| ID | Transformation | Fixes |
|---|---|---|
| T-01 | Extract configuration to an environment-based settings module | AP-01, AP-10, AP-20 (config literals) |
| T-02 | Parameterize queries | AP-02 |
| T-03 | Split God class / fat routes into Model–View–Controller | AP-03, AP-07 |
| T-04 | Hash passwords with a standard KDF | AP-05 |
| T-05 | Allowlist serializers and safe logging | AP-04 |
| T-06 | Guard destructive/debug endpoints | AP-06 |
| T-07 | Centralized error handling with an error hierarchy | AP-15, AP-19 |
| T-08 | Remove N+1 with JOIN / eager loading / GROUP BY | AP-13 |
| T-09 | Wrap multi-step writes in a transaction | AP-11 |
| T-10 | Replace callback pyramids with async/await | AP-17 |
| T-11 | App factory + dependency injection (composition root) | AP-08, AP-09 |
| T-12 | Dedicated validation layer | AP-14 |
| T-13 | Move duplicated rules into the model / service | AP-16, AP-07 |
| T-14 | Replace deprecated APIs | AP-18 |
| T-15 | Named constants and meaningful names | AP-20, AP-21 |
| T-16 | Remove dead code, replace prints with a logger, simplify conditionals | AP-22, AP-23, AP-24 |
| T-17 | Enforce referential integrity on delete | AP-12 |
| T-18 | Replace mutable globals with scoped state | AP-09 |

Recommended execution order: T-01 → T-11 → T-02/T-04/T-09 (models) → T-13/T-08 → T-12 → T-03 (controllers + views) → T-07 → T-05/T-06 → T-14/T-15/T-16/T-17/T-18 → validation.

---

## T-01 — Extract configuration to an environment-based settings module
**Fixes:** AP-01, AP-10.

Python — before:
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "my-super-secret-key"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```

Python — after (`src/config/settings.py`):
```python
import logging
import os
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.warning("%s not set; using an ephemeral development value", name)
        value = secrets.token_hex(32)
    return value


@dataclass(frozen=True)
class Settings:
    secret_key: str
    debug: bool
    host: str
    port: int
    database_path: str
    cors_origins: str


def load_settings() -> Settings:
    return Settings(
        secret_key=_secret("SECRET_KEY"),
        debug=_bool("FLASK_DEBUG", False),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),      # same default as the original
        database_path=os.environ.get("DATABASE_PATH", "app.db"),
        cors_origins=os.environ.get("CORS_ORIGINS", "*"),
    )
```

Node.js — before:
```js
const config = { dbPass: "prod_password_123", paymentKey: "pk_live_abc", port: 3000 };
```

Node.js — after (`src/config/settings.js`):
```js
const settings = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  databaseUrl: process.env.DATABASE_URL || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || null, // no secret default
  adminToken: process.env.ADMIN_TOKEN || null,
});

module.exports = settings;
```

Also create `.env.example` listing every variable with fake values.

---

## T-02 — Parameterize queries
**Fixes:** AP-02.

Python (sqlite3) — before:
```python
cursor.execute("SELECT * FROM users WHERE email = '" + email + "' AND password = '" + password + "'")

query = "SELECT * FROM products WHERE 1=1"
if term:
    query += " AND name LIKE '%" + term + "%'"
cursor.execute(query)
```

Python — after:
```python
row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

clauses, params = ["1=1"], []
if term:
    clauses.append("(name LIKE ? OR description LIKE ?)")
    params += [f"%{term}%", f"%{term}%"]
if category:
    clauses.append("category = ?")
    params.append(category)
rows = conn.execute(f"SELECT * FROM products WHERE {' AND '.join(clauses)}", params).fetchall()
```
(Only constant SQL fragments are joined; every value goes through `params`.)

Node.js (sqlite3) — before:
```js
db.all(`SELECT * FROM articles WHERE title LIKE '%${req.query.q}%'`, cb);
```

Node.js — after:
```js
const articles = await db.all('SELECT * FROM articles WHERE title LIKE ?', [`%${term}%`]);
```

---

## T-03 — Split God class / fat routes into Model–View–Controller
**Fixes:** AP-03, AP-07.

Before (everything in one handler: routing + SQL + business rule + side effect):
```python
@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    total = 0
    for item in data["items"]:
        product = db.execute("SELECT * FROM products WHERE id = " + str(item["product_id"])).fetchone()
        if product["stock"] < item["qty"]:
            return jsonify({"error": "no stock"}), 400
        total += product["price"] * item["qty"]
    db.execute("INSERT INTO orders (user_id, total) VALUES (" + str(data["user_id"]) + ", " + str(total) + ")")
    db.commit()
    print("SENDING EMAIL...")
    return jsonify({"total": total}), 201
```

After — Model (`src/models/order_model.py`): data access + domain rule
```python
class OrderModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def create(self, user_id: int, items: list[dict]) -> dict:
        conn = self._get_connection()
        with conn:  # transaction (T-09)
            total = 0.0
            for item in items:
                product = conn.execute(
                    "SELECT id, name, price, stock FROM products WHERE id = ?", (item["product_id"],)
                ).fetchone()
                if product is None:
                    raise NotFoundError(f"Product {item['product_id']} not found")
                if product["stock"] < item["quantity"]:
                    raise ValidationError(f"Insufficient stock for {product['name']}")
                total += product["price"] * item["quantity"]
            cur = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))
            # ... insert items and decrement stock with parameterized queries
        return {"order_id": cur.lastrowid, "total": total}
```

After — Controller (`src/controllers/order_controller.py`): request flow only
```python
from flask import jsonify, request


class OrderController:
    def __init__(self, order_model, notification_service):
        self._orders = order_model                     # dependencies injected by the composition root (T-11)
        self._notifications = notification_service

    def create_order(self):
        payload = validate_order_payload(request.get_json(silent=True))   # T-12
        result = self._orders.create(payload["user_id"], payload["items"])
        self._notifications.order_created(result["order_id"], payload["user_id"])  # side effects live in a service
        return jsonify({"total": result["total"]}), 201                  # same response body as before
```

After — View (`src/views/order_routes.py`): URL bindings only
```python
from flask import Blueprint

def build_order_blueprint(controller) -> Blueprint:
    bp = Blueprint("orders", __name__)
    bp.add_url_rule("/orders", "create_order", controller.create_order, methods=["POST"])
    return bp
```

Node.js equivalent — before (`class ServerManager { setupRoutes(app) { app.post('/api/orders', (req, res) => { db.get(...); db.run(...); }) } }`); after:
```js
// src/views/routes.js
const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function buildRoutes({ orderController, reportController }) {
  const router = express.Router();
  router.post('/api/orders', asyncHandler(orderController.create));
  router.get('/api/reports/sales', asyncHandler(reportController.sales));
  return router;
}
module.exports = buildRoutes;

// src/controllers/orderController.js
function makeOrderController({ orderService }) {
  return {
    async create(req, res) {
      const input = validateOrder(req.body);               // T-12
      const result = await orderService.placeOrder(input);
      res.status(201).json({ id: result.orderId, total: result.total }); // same body as before
    },
  };
}
module.exports = makeOrderController;
```

---

## T-04 — Hash passwords with a standard KDF
**Fixes:** AP-05.

Python — before:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
...
cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, pwd))
```

Python — after (Werkzeug ships with Flask, no new dependency):
```python
from werkzeug.security import check_password_hash, generate_password_hash

def set_password(self, raw: str) -> None:
    self.password = generate_password_hash(raw)

def check_password(self, raw: str) -> bool:
    return check_password_hash(self.password, raw)

# login: fetch by e-mail, then verify in code
user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
if user is None or not check_password_hash(user["password"], raw_password):
    raise UnauthorizedError("Invalid credentials")
```

Legacy data (optional, when existing rows hold old hashes/plaintext):
```python
def verify_and_upgrade(user, raw):
    if user.password.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(user.password, raw)
    legacy_ok = hmac.compare_digest(user.password, hashlib.md5(raw.encode()).hexdigest())
    if legacy_ok:
        user.set_password(raw)  # upgrade on successful login
    return legacy_ok
```

Node.js — before:
```js
function hashIt(pwd) { return Buffer.from(pwd).toString('base64').split('').reverse().join('').slice(0, 12); } // reversible, unsalted
```

Node.js — after (built-in `crypto`):
```js
const crypto = require('crypto');
const KEY_LENGTH = 64;

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, KEY_LENGTH).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

function verifyPassword(password, stored) {
  const [scheme, salt, hash] = String(stored).split('$');
  if (scheme !== 'scrypt') return false;
  const candidate = crypto.scryptSync(password, salt, KEY_LENGTH);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
```
Never assign a default password when the client omits it — reject the request (400) or require the field for new accounts.

---

## T-05 — Allowlist serializers and safe logging
**Fixes:** AP-04.

Before:
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password, "role": self.role}

@app.route("/health")
def health():
    return {"status": "ok", "secret_key": app.config["SECRET_KEY"], "debug": True}
```
```js
console.log(`Charging card ${card} with key ${config.gatewayKey}`);
```

After:
```python
PUBLIC_USER_FIELDS = ("id", "name", "email", "role", "active", "created_at")

def serialize_user(user) -> dict:
    return {field: getattr(user, field) for field in PUBLIC_USER_FIELDS}

def health():
    return {"status": "ok", "database": "connected"}   # no secrets/config
```
```js
const maskCard = (card) => `****${String(card).slice(-4)}`;
logger.info(`Charging card ${maskCard(card)}`); // never log keys or full card numbers
```

---

## T-06 — Guard destructive/debug endpoints
**Fixes:** AP-06.

Before:
```python
@app.route("/admin/query", methods=["POST"])
def run_query():
    cursor.execute(request.get_json()["sql"])
```

After — middleware/decorator (`src/middlewares/admin_guard.py`):
```python
import hmac
from functools import wraps
from flask import current_app, request

def admin_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cfg = current_app.config
        token = request.headers.get("X-Admin-Token", "")
        if not cfg["ADMIN_ENDPOINTS_ENABLED"] or not cfg["ADMIN_TOKEN"] \
                or not hmac.compare_digest(token, cfg["ADMIN_TOKEN"]):
            raise ForbiddenError("Admin endpoints are disabled or token is invalid")
        return view(*args, **kwargs)
    return wrapper
```

Controller keeps the route but restricts what it can do:
```python
READ_ONLY = re.compile(r"^\s*select\b[^;]*;?\s*$", re.IGNORECASE)

@admin_only
def run_query():
    sql = (request.get_json(silent=True) or {}).get("sql", "")
    if not READ_ONLY.match(sql):
        raise ValidationError("Only a single read-only SELECT is allowed")
    rows = admin_model.read_only_query(sql)   # executes on a read-only connection (e.g. sqlite "file:...?mode=ro")
    return jsonify({"data": rows}), 200   # keep the original envelope
```

Node.js:
```js
const crypto = require('crypto');

function adminGuard(settings) {
  return (req, res, next) => {
    const token = Buffer.from(req.get('X-Admin-Token') || '');
    const expected = Buffer.from(settings.adminToken || '');
    const ok = settings.adminToken && token.length === expected.length && crypto.timingSafeEqual(token, expected);
    return ok ? next() : next(new ForbiddenError('Admin token required'));
  };
}
```
The guard must be **closed by default**: with no token configured it denies (403), it never falls through to `next()`/the view. An opt-in guard leaves the finding open — see `mvc-guidelines.md` §9 exception 2.

```js
// wrong: without ADMIN_TOKEN the route stays public
function createAdminGuard({ adminToken }) {
  if (!adminToken) return (req, res, next) => next();
  ...
}

// right: closed by default, enabled by explicit configuration
function createAdminGuard({ adminToken, adminEndpointsEnabled }) {
  return (req, res, next) => {
    if (!adminEndpointsEnabled || !adminToken) return next(new ForbiddenError('Admin endpoints disabled'));
    return tokensMatch(req.get(ADMIN_TOKEN_HEADER) || '', adminToken) ? next() : next(new ForbiddenError());
  };
}
```

Use guards on routes that were already "admin"/debug by nature only when allowed by the contract rules (see mvc-guidelines §9); otherwise list authentication as a remaining item.

Privilege escalation on public endpoints — before:
```python
role = data.get("role", "user")          # anyone can send {"role": "admin"}
if role not in ("user", "admin", "manager"):
    raise ValidationError("Role inválido")
```

After (self-registration can only create the least-privileged role; the route, the method and the 201 stay the same):
```python
DEFAULT_ROLE = "user"
SELF_SIGNUP_ROLES = (DEFAULT_ROLE,)          # roles an anonymous caller may ask for
PRIVILEGED_ROLES = ("admin", "manager")      # only an authenticated admin may grant these

def role_for_public_signup(payload: dict) -> str:
    requested = payload.get("role", DEFAULT_ROLE)
    if requested not in USER_ROLES:
        raise ValidationError("Role inválido")          # same message as before
    if requested not in SELF_SIGNUP_ROLES:
        raise ForbiddenError("Não é possível criar usuário com esse role")
    return requested
```
The same rule applies to updates: while the endpoint has no guard proving who is calling, it must not change `role`/`is_admin`/`permissions` (reject with 403, or ignore the field and say so in "Contract Changes"). Escalating to "needs authentication" is not an option here — see `mvc-guidelines.md` §9 exception 8.

Predictable tokens (`'token-' + str(user.id)`) → sign them with the framework's utilities (e.g. `itsdangerous.URLSafeTimedSerializer(secret_key).dumps({"user_id": id})`, or HMAC with `crypto.createHmac('sha256', secret)`), keeping the same response field.

---

## T-07 — Centralized error handling with an error hierarchy
**Fixes:** AP-15, AP-19.

Before (repeated in every handler):
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
```js
db.get(sql, params, (err, row) => { if (err) return res.status(500).send("Erro DB"); ... });
```

After — Python (`src/middlewares/error_handler.py`):
```python
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class ValidationError(AppError): status_code = 400
class UnauthorizedError(AppError): status_code = 401
class ForbiddenError(AppError): status_code = 403
class NotFoundError(AppError): status_code = 404
class ConflictError(AppError): status_code = 409


def register_error_handlers(app, error_key="erro"):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        response = jsonify({error_key: err.description})
        response.status_code = err.code
        # keep the headers the framework had set (Allow on 405, WWW-Authenticate on 401...)
        for header, value in (err.get_response().headers or {}).items():
            if header.lower() not in {"content-type", "content-length"}:
                response.headers[header] = value
        return response

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Unhandled error")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```

After — Node.js (`src/middlewares/errorHandler.js` + `asyncHandler.js`):
```js
class AppError extends Error {
  constructor(message, statusCode = 500) { super(message); this.statusCode = statusCode; }
}

const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

function errorHandler(err, req, res, next) { // eslint-disable-line no-unused-vars
  if (err instanceof AppError) return res.status(err.statusCode).send(err.message); // keep original format (text or JSON)
  if (err.type === 'entity.parse.failed') return res.status(400).send('Bad Request');
  console.error(err);
  return res.status(500).send('Erro interno');
}

module.exports = { AppError, asyncHandler, errorHandler };
```
Match the original error format per endpoint (plain text vs JSON) so clients keep working.

---

## T-08 — Remove N+1 with JOIN / eager loading / GROUP BY
**Fixes:** AP-13.

Raw SQL — before:
```python
orders = conn.execute("SELECT * FROM orders").fetchall()
for order in orders:
    items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
    for item in items:
        product = conn.execute("SELECT name FROM products WHERE id = ?", (item["product_id"],)).fetchone()
```

Raw SQL — after (1 query, grouped in memory):
```python
rows = conn.execute("""
    SELECT o.id, o.user_id, o.status, o.total, o.created_at,
           i.product_id, i.quantity, i.unit_price, p.name AS product_name
    FROM orders o
    LEFT JOIN order_items i ON i.order_id = o.id
    LEFT JOIN products p ON p.id = i.product_id
    ORDER BY o.id, i.id
""").fetchall()
orders = {}
for r in rows:
    order = orders.setdefault(r["id"], {"id": r["id"], "user_id": r["user_id"], "status": r["status"],
                                        "total": r["total"], "created_at": r["created_at"], "items": []})
    if r["product_id"] is not None:
        order["items"].append({"product_id": r["product_id"], "product_name": r["product_name"] or "Unknown",
                               "quantity": r["quantity"], "unit_price": r["unit_price"]})
result = list(orders.values())
```

SQLAlchemy — before:
```python
for order in Order.query.all():
    customer = Customer.query.get(order.customer_id)   # 1 query per order
```
SQLAlchemy — after:
```python
from sqlalchemy.orm import joinedload
tasks = db.session.execute(
    db.select(Order).options(joinedload(Order.customer), joinedload(Order.product))
).scalars().all()
```

Counting — before: one `COUNT` per status / per category. After:
```python
counts = dict(db.session.execute(
    db.select(Order.status, db.func.count(Order.id)).group_by(Order.status)
).all())
```

Node.js — before: `authors.forEach(a => db.all(posts..., (posts) => posts.forEach(p => db.get(comments...))))`. After:
```js
const rows = await db.all(`
  SELECT a.id AS author_id, a.name, p.id AS post_id, p.title, COUNT(c.id) AS comments
  FROM authors a
  LEFT JOIN posts p ON p.author_id = a.id
  LEFT JOIN comments c ON c.post_id = p.id
  GROUP BY a.id, p.id
  ORDER BY a.id, p.id`);
// then group rows by author_id in memory, preserving the original response shape
```

---

## T-09 — Wrap multi-step writes in a transaction
**Fixes:** AP-11.

Python sqlite3 — before:
```python
cursor.execute("INSERT INTO orders ...")
for item in items:
    cursor.execute("INSERT INTO order_items ...")
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", ...)
db.commit()
```
Python — after:
```python
with conn:   # commits on success, rolls back on any exception
    cur = conn.execute("INSERT INTO orders (user_id, status, total) VALUES (?, 'pending', ?)", (user_id, total))
    for item in items:
        conn.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                     (cur.lastrowid, item["product_id"], item["quantity"], item["unit_price"]))
        updated = conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",   # conditional update avoids overselling
            (item["quantity"], item["product_id"], item["quantity"]),
        ).rowcount
        if updated == 0:
            raise ValidationError("Insufficient stock")
```

SQLAlchemy:
```python
try:
    db.session.add(order)
    db.session.commit()
except SQLAlchemyError:
    db.session.rollback()
    raise
```

Node.js sqlite3 (with promise helpers from T-10):
```js
async function withTransaction(db, work) {
  await db.run('BEGIN IMMEDIATE');
  try {
    const result = await work();
    await db.run('COMMIT');
    return result;
  } catch (err) {
    await db.run('ROLLBACK');
    throw err;
  }
}

const subscriptionId = await withTransaction(db, async () => {
  const { lastID } = await db.run('INSERT INTO subscriptions (customer_id, plan_id) VALUES (?, ?)', [customerId, planId]);
  await db.run('INSERT INTO invoices (subscription_id, amount, status) VALUES (?, ?, ?)', [lastID, price, 'PAID']);
  await db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
  return lastID;
});
```
With a single shared connection, serialize transactions (e.g. a simple promise queue/mutex) so concurrent requests cannot interleave statements.

---

## T-10 — Replace callback pyramids with async/await
**Fixes:** AP-17.

Before:
```js
db.get(q1, [a], (err, plan) => {
  db.get(q2, [b], (err, user) => {
    db.run(q3, [c], function (err) {
      const id = this.lastID;
      db.run(q4, [id], (err) => res.json({ id }));
    });
  });
});
```

After — promise wrapper (`src/models/database.js`):
```js
const sqlite3 = require('sqlite3');

function openDatabase(filename) {
  const raw = new sqlite3.Database(filename);
  return {
    run: (sql, params = []) => new Promise((resolve, reject) =>
      raw.run(sql, params, function onRun(err) { return err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); })),
    get: (sql, params = []) => new Promise((resolve, reject) =>
      raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)))),
    all: (sql, params = []) => new Promise((resolve, reject) =>
      raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)))),
    exec: (sql) => new Promise((resolve, reject) => raw.exec(sql, (err) => (err ? reject(err) : resolve()))),
    close: () => new Promise((resolve, reject) => raw.close((err) => (err ? reject(err) : resolve()))),
  };
}
module.exports = { openDatabase };
```

After — flat flow:
```js
const plan = await planModel.findActiveById(planId);
if (!plan) throw new AppError('Plan not found', 404);
const customer = await customerModel.findByEmail(email);
const subscriptionId = await subscriptionService.subscribe(customer.id, plan);
res.json({ id: subscriptionId });
```

---

## T-11 — App factory + dependency injection (composition root)
**Fixes:** AP-08, AP-09.

Python — before (`app.py`):
```python
app = Flask(__name__)
app.config[...] = ...
db.init_app(app)
app.register_blueprint(order_bp)
with app.app_context():
    db.create_all()          # runs on import
```

Python — after (`src/app.py`):
```python
from flask import Flask
from flask_cors import CORS

from src.config.settings import load_settings
from src.middlewares.error_handler import register_error_handlers
from src.models.database import init_database
from src.views.order_routes import order_bp


def create_app(overrides: dict | None = None) -> Flask:
    settings = load_settings()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        DEBUG=settings.debug,
        DATABASE_PATH=settings.database_path,
        **(overrides or {}),
    )
    CORS(app, origins=settings.cors_origins)
    init_database(app)
    app.register_blueprint(order_bp)
    register_error_handlers(app)
    return app
```
Root `app.py` (keeps `python app.py`):
```python
from src.app import create_app
from src.config.settings import load_settings

app = create_app()

if __name__ == "__main__":
    settings = load_settings()
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
```
Scripts (e.g. `seed.py`) use `app = create_app()` + `with app.app_context():`.

Node.js — before:
```js
class ServerManager { constructor() { this.db = new sqlite3.Database(':memory:'); } ... }
const manager = new ServerManager(); manager.initDb(); manager.setupRoutes(app); app.listen(3000);
```

Node.js — after:
```js
// src/createApp.js
function createApp({ db, settings }) {
  const orderModel = makeOrderModel(db);
  const orderService = makeOrderService({ db, orderModel, settings });
  const orderController = makeOrderController({ orderService });

  const app = express();
  app.use(express.json());
  app.use(buildRoutes({ orderController }));
  app.use(notFoundHandler);
  app.use(errorHandler);
  return app;
}

// src/app.js (entry point)
(async () => {
  const db = openDatabase(settings.databaseUrl);
  await initSchema(db);
  await seed(db);
  createApp({ db, settings }).listen(settings.port, () => console.log(`Listening on ${settings.port}`));
})();
```

---

## T-12 — Dedicated validation layer
**Fixes:** AP-14.

Before:
```python
data = request.get_json()
if data["price"] < 0:           # TypeError when price is "10"; AttributeError when body is empty
    return jsonify({"error": "invalid"}), 400
```

After (`src/utils/validators.py` or `src/controllers/validators.py`):
```python
def require_json_object(payload) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload


def number_field(payload: dict, name: str, *, required=True, minimum=None, integer=False, message=None):
    value = payload.get(name)
    if value is None:
        if required:
            raise ValidationError(message or f"{name} é obrigatório")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and not isinstance(value, int)):
        raise ValidationError(f"{name} deve ser numérico")
    if minimum is not None and value < minimum:
        raise ValidationError(message or f"{name} deve ser >= {minimum}")
    return value


def choice_field(payload: dict, name: str, allowed: tuple[str, ...], default=None):
    value = payload.get(name, default)
    if value not in allowed:
        raise ValidationError(f"{name} inválido")
    return value
```
Controller:
```python
payload = require_json_object(request.get_json(silent=True))
price = number_field(payload, "price", minimum=0)
quantity = number_field(payload, "quantity", minimum=1, integer=True)
```

Node.js:
```js
function validateOrder(body) {
  const { cust, mail, prod_id: productId, qty } = body || {};
  if (!cust || !mail || !productId) throw new AppError('Bad Request', 400);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) throw new AppError('Bad Request', 400);
  if (!Number.isInteger(qty) || qty < 1) throw new AppError('Bad Request', 400);
  return { customerName: cust, email: mail, productId: Number(productId), quantity: qty };
}
```
Keep the messages/status codes the original returned for the same invalid inputs.

---

## T-13 — Move duplicated rules into the model / service
**Fixes:** AP-16, AP-07.

Before (same rule copied in several routes):
```python
if inv.due_date:
    if inv.due_date < datetime.utcnow():
        if inv.status != 'paid' and inv.status != 'cancelled':
            overdue = True
        else:
            overdue = False
    else:
        overdue = False
else:
    overdue = False
```

After (`src/models/invoice.py`) — one implementation, reused everywhere:
```python
CLOSED_STATUSES = frozenset({"paid", "cancelled"})

class Invoice(db.Model):
    ...
    def is_overdue(self, now: datetime | None = None) -> bool:
        now = now or utcnow_naive()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

    def to_dict(self, *, include_overdue=False) -> dict:
        data = {...}
        if include_overdue:
            data["overdue"] = self.is_overdue()
        return data
```
Row-to-dict mappings duplicated across queries → one `_row_to_product(row)` helper in the model; list functions differing only by filter → one function with an optional parameter.

---

## T-14 — Replace deprecated APIs
**Fixes:** AP-18.

```python
# before
from datetime import datetime
created_at = db.Column(db.DateTime, default=datetime.utcnow)
invoice = Invoice.query.get(invoice_id)
if datetime.utcnow() > invoice.due_date: ...

# after
from datetime import datetime, timezone

def utcnow_naive() -> datetime:
    """Current UTC time as a naive datetime (keeps compatibility with naive columns already stored)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at = db.Column(db.DateTime, default=utcnow_naive)
invoice = db.session.get(Invoice, invoice_id)
if utcnow_naive() > invoice.due_date: ...
```
```python
# before: Invoice.query.filter_by(customer_id=cid).all()
# after:
db.session.execute(db.select(Invoice).filter_by(customer_id=cid)).scalars().all()
```
```js
// before
const buf = new Buffer(str);
const parsed = url.parse(req.url);
app.use(require('body-parser').json());
// after
const buf = Buffer.from(str);
const parsed = new URL(req.url, `http://${req.headers.host}`);
app.use(express.json());
```
Deprecated/vulnerable npm dependencies: apply the compatible fix (`npm audit fix` without `--force`, or bump to the maintained minor/major only after checking the changelog), then rerun validation. Keep the naive-vs-aware datetime choice consistent with data already stored to avoid comparison errors.

---

## T-15 — Named constants and meaningful names
**Fixes:** AP-20, AP-21.

Before:
```python
if total > 10000:
    d = total * 0.1
elif total > 5000:
    d = total * 0.05
```
```js
let c = req.body.cust; let m = req.body.mail; let q = req.body.qty;
```

After:
```python
DISCOUNT_TIERS = (          # (minimum revenue, rate) — highest first
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)

def discount_for(revenue: float) -> float:
    for threshold, rate in DISCOUNT_TIERS:
        if revenue > threshold:
            return revenue * rate
    return 0.0
```
```js
// contract field names stay the same; internal names become meaningful
const { cust: customerName, mail: customerEmail, qty: quantity } = req.body;
const ORDER_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
```

---

## T-16 — Remove dead code, replace prints with a logger, simplify conditionals
**Fixes:** AP-22, AP-23, AP-24.

Before:
```python
import os, sys, json, time      # unused
print("Order created: " + str(order.id))

def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False

if type(items) == list: ...
```

After:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Order created: id=%s", order.id)

def is_admin(self) -> bool:
    return self.role == "admin"

if isinstance(items, list): ...
```
Delete functions/modules/config keys with no references (confirm with `grep -rn name`). Unused but meaningful services (e.g. notification) should be either wired into the use case that needs them or removed — never left orphaned.

---

## T-17 — Enforce referential integrity on delete
**Fixes:** AP-12.

Before:
```js
app.delete('/api/customers/:id', (req, res) => {
  db.run('DELETE FROM customers WHERE id = ?', [req.params.id], () => res.send('deleted')); // subscriptions/invoices orphaned, err ignored
});
```

After — service with transaction (schema without FKs):
```js
async function deleteCustomer(customerId) {
  return withTransaction(db, async () => {
    await db.run('DELETE FROM invoices WHERE subscription_id IN (SELECT id FROM subscriptions WHERE customer_id = ?)', [customerId]);
    await db.run('DELETE FROM subscriptions WHERE customer_id = ?', [customerId]);
    const { changes } = await db.run('DELETE FROM customers WHERE id = ?', [customerId]);
    return changes;
  });
}
```
Schema-level alternative: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE` + `PRAGMA foreign_keys = ON`.

SQLAlchemy:
```python
invoices = db.relationship("Invoice", back_populates="customer", cascade="all, delete-orphan")
# nullable references (e.g. invoice.tag_id) → set to NULL before deleting the parent
db.session.execute(db.update(Invoice).where(Invoice.tag_id == tag.id).values(tag_id=None))
```
If the business decision is unclear (delete vs soft-delete vs block), prefer blocking/cleaning inside a transaction and report the choice.

---

## T-18 — Replace mutable globals with scoped state
**Fixes:** AP-09.

Before:
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("app.db", check_same_thread=False)
    return db_connection
```
```js
let globalCache = {};
function logAndCache(key, data) { globalCache[key] = data; }
module.exports = { globalCache, logAndCache };
```

After — per-request connection (Flask):
```python
import sqlite3
from flask import current_app, g

def get_connection() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_connection(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_database(app) -> None:
    app.teardown_appcontext(close_connection)
    with app.app_context():
        create_schema(get_connection())
```

After — state owned by an injected instance (Node.js):
```js
class RecentActivityCache {
  constructor(maxEntries = 1000) { this.entries = new Map(); this.maxEntries = maxEntries; }
  set(key, value) {
    if (this.entries.size >= this.maxEntries) this.entries.delete(this.entries.keys().next().value);
    this.entries.set(key, value);
  }
}
// created once in createApp() and passed to the service that needs it — or removed if nothing reads it
```
