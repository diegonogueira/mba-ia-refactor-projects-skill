# Project Analysis Heuristics (Phase 1)

Goal: produce a factual picture of the project — stack, database, domain, entry point, endpoints and current architecture — without modifying anything. Every statement must be backed by a file you read.

## Table of contents
1. File inventory
2. Language detection
3. Framework and version detection
4. Database detection
5. Entry point and run command
6. Endpoint inventory
7. Architecture mapping and classification
8. Domain inference
9. Consistency checks before printing

---

## 1. File inventory

- Start from the injected snapshot (or `find . -type f` excluding `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`, `target`, `.claude`).
- Classify each file:

| Class | Examples | Counted as "Source files"? |
|---|---|---|
| Application source | `*.py`, `*.js`, `*.ts`, `*.go`, `*.java`, `*.rb`, `*.php`, `*.cs`, `*.ex` (including seed/migration scripts and empty `__init__.py`) | **Yes** |
| Manifests / lockfiles | `requirements.txt`, `pyproject.toml`, `package.json`, `package-lock.json`, `go.mod`, `pom.xml` | No (used for stack detection) |
| Docs / collections | `README.md`, `api.http`, `*.postman_collection.json` | No (used for domain and endpoint hints) |
| Generated / runtime | `*.db`, `*.sqlite`, logs, `*.pyc` | No |

- Count lines of code with `wc -l` over the application source files (report as `~N lines of code`).
- If some source files are empty (e.g. `__init__.py`), still count them but you may note it: `15 files analyzed (3 empty __init__.py)`.

## 2. Language detection

Use the first matching evidence; confirm with file extensions.

| Evidence | Language |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, majority of `*.py` | Python |
| `package.json` + `*.js` / `*.mjs` / `*.cjs` | JavaScript (Node.js) |
| `package.json` + `tsconfig.json` or `*.ts` | TypeScript (Node.js) |
| `go.mod` | Go |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj`, `*.sln` | C# (.NET) |
| `mix.exs` | Elixir |
| `Cargo.toml` | Rust |

Runtime version hints: `.python-version`, `runtime.txt`, `engines` in `package.json`, `.nvmrc`, `Dockerfile` `FROM` line.

## 3. Framework and version detection

1. Look for the framework in the manifest; take the **version** from the pin (`flask==3.1.1`) or, for ranges (`^4.18.2`), from the lockfile (`package-lock.json` → `node_modules/express` → `version`). Report the range and the resolved version when they differ, e.g. `Express 4.x (^4.18.2 in package.json)`.
2. Confirm with code signatures:

| Framework | Manifest name | Code signature |
|---|---|---|
| Flask | `flask` | `Flask(__name__)`, `@app.route`, `app.add_url_rule`, `Blueprint(` |
| FastAPI | `fastapi` | `FastAPI()`, `@app.get`, `APIRouter(` |
| Django | `django` | `manage.py`, `settings.py`, `urls.py`, `models.Model` |
| Express | `express` | `require('express')` / `import express`, `express()`, `app.get(`, `express.Router()` |
| NestJS | `@nestjs/core` | `@Controller(`, `@Module(` |
| Fastify / Koa / Hapi | `fastify` / `koa` / `@hapi/hapi` | `fastify(`, `new Koa()`, `Hapi.server(` |
| Spring Boot | `spring-boot-starter-web` | `@RestController`, `@SpringBootApplication` |
| Rails / Laravel | `rails` / `laravel/framework` | `config/routes.rb` / `routes/web.php` |
| Gin / Echo | `github.com/gin-gonic/gin` / `labstack/echo` | `gin.Default()` / `echo.New()` |

3. List the other runtime dependencies (`Dependencies:` line): CORS, ORM, validation, HTTP clients, env loaders. Flag dependencies declared but never imported (grep the package import name across the source) — they feed the audit.

## 4. Database detection

| Evidence | Engine / access style |
|---|---|
| `import sqlite3`, `sqlite3.connect(`, `require('sqlite3')`, `new sqlite3.Database(` | SQLite, raw SQL driver |
| `':memory:'` as database path | SQLite in memory (data resets on every boot) |
| `SQLALCHEMY_DATABASE_URI`, `flask_sqlalchemy`, `db.Model` | SQLAlchemy ORM (engine from the URI scheme) |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL |
| `mysql`, `mysql2`, `pymysql` | MySQL |
| `mongoose`, `pymongo`, `mongodb://` | MongoDB |
| `prisma/schema.prisma`, `sequelize`, `typeorm`, `knex` | Node ORMs / query builders |

Table / entity names:
- Raw SQL: `grep -n "CREATE TABLE" -r .` → name after `CREATE TABLE [IF NOT EXISTS]`.
- SQLAlchemy: `__tablename__ = '...'` (or class name when absent).
- Django: `class X(models.Model)`; Sequelize/TypeORM: `define('x'` / `@Entity`.
- Also record where the schema is created (e.g. at import time, inside a class constructor, in a seed script) and where seed data lives.

## 5. Entry point and run command

| Stack | Where to look |
|---|---|
| Python | `if __name__ == "__main__":` → `app.run(...)` (host, port, debug); README "how to run"; `wsgi.py`; `FLASK_APP` |
| Node.js | `package.json` → `main` and `scripts.start`; `app.listen(` / `server.listen(` |
| Others | `main()` functions, `Dockerfile` `CMD`, `Procfile` |

Record: entry file, start command, port, required setup steps (e.g. `python seed.py` before first boot), and whether the database is created automatically.

## 6. Endpoint inventory

Search route declarations and record **method, path, handler, file:line** for every route:

| Framework | Search pattern (`grep -rn`) |
|---|---|
| Flask | `@app.route\|@[a-z_]*bp\.route\|add_url_rule\|\.route(` — method list in `methods=[...]` (default `GET`); blueprint `url_prefix` in `Blueprint(` or `register_blueprint(` |
| FastAPI | `@app\.(get\|post\|put\|patch\|delete)\|@router\.` |
| Express | `app\.(get\|post\|put\|patch\|delete\|all)(\|router\.(get\|post\|put\|patch\|delete)(\|app\.use('/` (router prefixes) |
| Django | `path(\|re_path(` in `urls.py` |
| Spring | `@(Get\|Post\|Put\|Delete\|Request)Mapping` |

Also collect from `api.http` / Postman collections / README the example payloads — they are the best inputs for the Phase 3 smoke test.

## 7. Architecture mapping and classification

For every source file, mark which responsibilities it contains (grep evidence in parentheses):

| Responsibility | Python signals | Node.js signals |
|---|---|---|
| Routing | `@app.route`, `add_url_rule`, `Blueprint` | `app.get(`, `router.post(` |
| HTTP handling | `request.get_json`, `request.args`, `jsonify` | `req.body`, `req.params`, `res.status(`, `res.json(` |
| Business rules | calculations, status transitions, discounts, stock checks, aggregations | same |
| Data access | `cursor.execute`, `db.session`, `Model.query` | `db.run(`, `db.get(`, `db.all(`, `.query(` |
| Configuration | `app.config[...]`, constants with keys/passwords | `config = {`, `process.env` |
| External side effects | `smtplib`, `requests.`, prints simulating e-mail/SMS | `nodemailer`, `fetch(`, `axios` |

Classify the architecture with the first category that matches:

| Category | Signals | Example wording |
|---|---|---|
| **Monolithic single class / file** | One class or file holds routing + data access + business rules (+ schema/seed) | `Monolítica — uma única classe concentra rotas, SQL, regras de negócio e seed` |
| **Flat modules without real layers** | A few root files named like layers (`models.py`, `controllers.py`) but responsibilities leak (SQL + business rules in "models", validation + side effects in "controllers", routes with SQL in `app.py`) | `Monolítica — tudo em N arquivos na raiz, sem separação real de camadas` |
| **Partially layered** | Folders `models/`, `routes/`, `services/`, `utils/` exist, but routes contain queries and business rules, there are no controllers, services/helpers are unused, config is hardcoded | `Parcialmente em camadas — models/routes/services existem, mas rotas concentram regra de negócio e acesso a dados` |
| **Layered MVC** | Routes only map URLs, controllers orchestrate, models own data, config externalized | `MVC em camadas` |
| **Clean / Hexagonal** | Ports/adapters, use cases, repositories behind interfaces | `Clean Architecture` |

## 8. Domain inference

Combine: table/entity names, route prefixes, seed data, README title and field names. Describe it as `<Domain> API (<main entities>)`, keeping entity names as they appear in the code, e.g. `E-commerce API (produtos, pedidos, usuários)`, `Blog API (posts, comments, authors)`, `Inventory API (items, warehouses, movements)`.

## 9. Consistency checks before printing

- The number of source files equals the inventory list.
- Framework version comes from a manifest/lockfile, not from memory.
- Every endpoint appears once with method + path; blueprint/router prefixes applied.
- Tables listed match schema declarations (not guesses from route names).
- Print using `report-template.md` → "Phase 1 output".
