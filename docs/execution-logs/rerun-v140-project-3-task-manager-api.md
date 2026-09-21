# Reexecução da skill (v1.4.0) — Projeto 3: `task-manager-api` (Python/Flask)

Execução com a skill v1.4.0, que fecha o padrão sistêmico identificado na varredura finding-a-finding (guard fechado por padrão, headers do framework no contrato, sem segredo em log/seed).

Diferente das execuções de `docs/execution-logs/project-3-*.md`, aqui a Fase 1 analisa o **código já refatorado** — por isso a arquitetura detectada é "MVC em camadas" e os achados são o que sobrou.

```bash
cd task-manager-api
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume 0c4f9654-57b5-4840-9128-37576fbbcc89 --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 18 | 4.5 min | US$ 1.75 | 17 |
| Fase 3 (após `y`) | 44 | 10.9 min | US$ 7.03 | 43 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3 (runtime local: 3.14.7; .venv existente: 3.12)
Framework:     Flask 3.1.3 (requirements.txt:1)
Dependencies:  Flask-SQLAlchemy 3.1.1, Flask-Cors 6.0.5, python-dotenv 1.2.3, Werkzeug 3.1.8, itsdangerous 2.2.0 (SQLAlchemy 2.0.54 resolvido no .venv, não declarado)
Domain:        API de gerenciamento de tarefas (users, tasks, categories) com login, busca, estatísticas e relatórios
Architecture:  MVC em camadas — config/models/services/controllers/views/middlewares/utils com app factory e DI
Source files:  39 files analyzed (~1569 lines of code; 8 __init__.py vazios)
Database:      SQLite via SQLAlchemy 2.x ORM (Flask-SQLAlchemy) — URI sqlite:///tasks.db → instance/tasks.db
DB tables:     users, categories, tasks
Entry point:   app.py → python app.py (port 5000, HOST/PORT configuráveis; setup: python seed.py)
Endpoints:     22 routes
  GET    /                              → HealthController.index (src/views/health_routes.py:7)
  GET    /health                        → HealthController.health (src/views/health_routes.py:8)
  GET    /tasks                         → TaskController.list_tasks (src/views/task_routes.py:7)
  POST   /tasks                         → TaskController.create_task (src/views/task_routes.py:8)
  GET    /tasks/search                  → TaskController.search_tasks (src/views/task_routes.py:9)
  GET    /tasks/stats                   → TaskController.task_stats (src/views/task_routes.py:10)
  GET    /tasks/<int:task_id>           → TaskController.get_task (src/views/task_routes.py:11)
  PUT    /tasks/<int:task_id>           → TaskController.update_task (src/views/task_routes.py:12)
  DELETE /tasks/<int:task_id>           → TaskController.delete_task (src/views/task_routes.py:13)
  GET    /users                         → UserController.list_users (src/views/user_routes.py:7)
  POST   /users                         → UserController.create_user (src/views/user_routes.py:8)
  GET    /users/<int:user_id>           → UserController.get_user (src/views/user_routes.py:9)
  PUT    /users/<int:user_id>           → UserController.update_user (src/views/user_routes.py:10)
  DELETE /users/<int:user_id>           → UserController.delete_user (src/views/user_routes.py:11)
  GET    /users/<int:user_id>/tasks     → UserController.list_user_tasks (src/views/user_routes.py:12)
  POST   /login                         → UserController.login (src/views/user_routes.py:14)
  GET    /categories                    → CategoryController.list_categories (src/views/category_routes.py:7)
  POST   /categories                    → CategoryController.create_category (src/views/category_routes.py:8)
  PUT    /categories/<int:category_id>  → CategoryController.update_category (src/views/category_routes.py:9)
  DELETE /categories/<int:category_id>  → CategoryController.delete_category (src/views/category_routes.py:11)
  GET    /reports/summary               → ReportController.summary (src/views/report_routes.py:7)
  GET    /reports/user/<int:user_id>    → ReportController.user_report (src/views/report_routes.py:8)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-3-rerun.md`](../../reports/audit-project-3-rerun.md). A mensagem terminou com:

```text
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Resposta enviada: `y`

## Fase 3 — saída

> Títulos rebaixados um nível para caber neste documento; conteúdo sem alterações.

```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

### New Project Structure

O projeto já estava em MVC (categoria "Already MVC" do §10 das guidelines), então a estrutura foi **preservada** e as correções foram feitas no lugar. A única adição é o guard administrativo:

```text
task-manager-api/
├── app.py                              # entrada fina: create_app() + app.run() (inalterado)
├── seed.py                             # agora exibe a senha sorteada uma única vez
├── requirements.txt                    # + sqlalchemy==2.0.54 (importada direto pelos models)
├── .env.example                        # + ADMIN_ENDPOINTS_ENABLED, ADMIN_TOKEN, SEED_PASSWORD
├── README.md                           # guard administrativo, senha do seed, logs sem hashes
└── src/
    ├── app.py                          # composition root: + engine options e config do guard
    ├── config/settings.py              # + admin_token / admin_endpoints_enabled (sem default aberto)
    ├── models/
    │   ├── database.py                 # ENGINE_OPTIONS hide_parameters + log só com o tipo do erro
    │   ├── user_model.py               # MAX_ROLE_LENGTH, MAX_PASSWORD_HASH_LENGTH, USER_NOT_FOUND_MESSAGE
    │   ├── task_model.py               # MAX_STATUS_LENGTH, TASK_NOT_FOUND_MESSAGE
    │   ├── category_model.py           # CATEGORY_NOT_FOUND_MESSAGE
    │   └── seed.py                     # senha do ambiente ou sorteada — nunca no código
    ├── services/                       # auth_service.py, report_service.py (reusa a mensagem do model)
    ├── controllers/
    │   ├── *_controller.py             # reusam as mensagens de contrato dos models
    │   └── validators/                 # delegam a regra de comprimento ao helper compartilhado
    ├── views/
    │   ├── user_routes.py              # DELETE /users/<id> envolvido pelo admin_only
    │   └── ...                         # demais blueprints e serializers inalterados
    ├── middlewares/
    │   ├── error_handler.py            # inalterado
    │   └── admin_guard.py              # NOVO — fechado por padrão, hmac.compare_digest
    └── utils/validators.py             # + validate_bounded_text / validate_optional_bounded_text
```

40 arquivos `.py` (~1676 linhas), contra 39 (~1569) antes.

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| AP-06 Unprotected Destructive Endpoints and Broken Authentication | CRITICAL | Partially fixed | T-06 | `src/middlewares/admin_guard.py`, `src/views/user_routes.py:12-14`, `src/config/settings.py:74-76`, `src/app.py:37-38` |
| AP-04 Sensitive Data Exposure in Logs — bound parameters of failed writes | HIGH | Fixed | T-05 | `src/models/database.py:13-15`, `src/models/database.py:30-32`, `src/app.py:36` |
| AP-04 Sensitive Data Exposure — privileged seed account with a well-known short password | HIGH | Fixed | T-05 | `src/models/seed.py:16-24`, `src/models/seed.py:60-70`, `seed.py:14-18` |
| AP-14 Missing Input Validation — tags length is never checked | MEDIUM | Fixed | T-12 | `src/controllers/validators/task_validator.py:73-83` |
| AP-16 Duplicated Code — validators and contract messages repeated across modules | MEDIUM | Fixed | T-13 | `src/utils/validators.py:17-33`, `src/models/user_model.py:20`, `src/models/task_model.py:30`, `src/models/category_model.py:16` |
| AP-22 Dependency Manifest Does Not Declare a Direct Dependency | LOW | Fixed | T-16 | `requirements.txt:5` |
| AP-20 Magic Numbers — raw column lengths breaking the file's own convention | LOW | Fixed | T-15 | `src/models/user_model.py:15-17`, `src/models/user_model.py:31-32`, `src/models/task_model.py:25`, `src/models/task_model.py:44` |

### Contract Changes

- **DELETE `/users/<id>`** — passa a responder **403** `{"error": "Endpoint administrativo desabilitado"}` enquanto `ADMIN_ENDPOINTS_ENABLED=true` **e** `ADMIN_TOKEN` não estiverem definidos. Com as duas variáveis e o header `X-Admin-Token` correto, volta a responder **200** com a mensagem original. É o endpoint que apaga a conta de qualquer pessoa **e todas as tasks dela** sem autenticação (exceção 2 do §9: destrutivo, fechado por padrão).
- **DELETE `/users/<id>` com id inexistente** — 404 → **403**: o guard roda antes do handler, então nem chega a consultar o banco. Consequência direta da mudança acima.
- **POST `/tasks` e PUT `/tasks/<id>` com `tags` acima de 500 caracteres** — 201/200 → **400** `{"error": "Tags muito longas"}`. Antes o valor era gravado ultrapassando o limite declarado da coluna (só não estourava porque SQLite ignora larguras de `VARCHAR`); em Postgres/MySQL isso era um 500 (exceções 3 e 6 do §9).
- **`python seed.py`** — os usuários de exemplo deixam de ter senha fixa no código. A senha vem de `SEED_PASSWORD` ou é sorteada e exibida **uma única vez** na saída do script. Nomes, e-mails e papéis dos usuários de exemplo continuam idênticos (as respostas de `GET /users` não mudam).
- *Nota, não é mudança de contrato:* `GET /reports/summary` passou de `tasks_by_status.pending = 7` para `6` no smoke test — o baseline contava a task de tags gigantes que agora é recusada. Mesma rota, mesmo status, mesmo shape.

### How to Run

```bash
pip install -r requirements.txt
cp .env.example .env          # opcional: SECRET_KEY, porta, CORS, guard administrativo
python seed.py                # anote a senha sorteada, ou defina SEED_PASSWORD antes
python app.py                 # http://localhost:5000

# para habilitar DELETE /users/<id>:
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=<token-longo-e-aleatorio> python app.py
curl -X DELETE -H "X-Admin-Token: <token>" http://127.0.0.1:5000/users/2
```

### Validation

```text
  ✓ Application boots without errors (python app.py, port 5000, log sem traceback)
  ✓ All endpoints respond correctly (46/50 checks idênticos ao baseline, 4 mudanças de contrato
    documentadas, 0 regressões; os 22 endpoints do inventário da Fase 1 foram exercitados)
  ✓ SQL injection probe: login com ' OR '1'='1 devolve 401 e /tasks/search com o mesmo payload
    devolve lista vazia — idêntico ao baseline (consultas já eram parametrizadas pelo ORM)
  ✓ Campo de privilégio de cliente anônimo: POST /users {"role":"admin"} → 403 e
    PUT /users/<id> {"role":"admin"} / {"active":...} → 403; o registro conferido depois
    mantém role='user' e active=true
  ✓ Endpoint destrutivo sem configuração alguma → 403 (e o usuário continua existindo);
    com token errado → 403; com ADMIN_ENDPOINTS_ENABLED + token correto → 200 e o registro é removido
  ✓ Erro forçado numa escrita (chave única duplicada): log passou de 6285 bytes contendo
    'scrypt:', '[SQL:' e 'parameters:' para 110 bytes com apenas "Falha ao gravar no banco
    (IntegrityError)" — nenhum hash de senha nos logs
  ✓ Header Allow preservado no 405 (DELETE /health → 405 com Allow: OPTIONS, HEAD, GET;
    a ordem varia entre boots porque o Werkzeug monta o header a partir de um set)
  ✓ Re-auditoria do catálogo sem novos sinais: nenhum segredo literal, nenhum debug=True/0.0.0.0,
    nenhum SQL concatenado, nenhum acesso a dados em controllers/views, nenhuma API depreciada,
    nenhum import não usado nos arquivos tocados
  ✗ Zero CRITICAL/HIGH anti-patterns remaining — AP-06 continua "Partially fixed" (ver abaixo)
```

### Remaining Items

- **AP-06 — autenticação obrigatória nas demais rotas (parte não corrigida).** Minha recomendação da Fase 2 era um `src/middlewares/auth.py` validando o token de login em **todos** os blueprints de escrita. Implementei apenas o guard administrativo no `DELETE /users/<id>`. **O que foi corrigido:** o endpoint destrutivo que apagava conta + tasks em cascata agora nasce fechado; a escalação de privilégio (`role`/`active` de cliente anônimo) está barrada com 403 na criação e na atualização, comprovada por probe; o token de login já é assinado com `itsdangerous` (não é previsível). **O que não foi:** `POST/PUT/DELETE` de tasks e categories, `PUT /users/<id>` e os relatórios seguem abertos, e o token emitido por `POST /login` continua sem ser verificado por nenhuma rota. Fechar isso transforma 200 em 401 para chamadas hoje legítimas — é mudança de contrato que o §9 das guidelines proíbe fazer sem a sua autorização. **Recomendação:** criar `src/middlewares/auth.py` com `AuthService.verify_token()` (`URLSafeTimedSerializer.loads` com `max_age`), carregar o usuário em `flask.g` e aplicar o guard aos blueprints de escrita; depois disso, mover `role`/`active` para uma rota administrativa autenticada em vez do 403 atual. Diga se quer que eu faça — é uma mudança pequena agora que o guard e a config já existem.

```text
================================
```

Dois pontos fora do escopo do refactor que notei e **não** toquei, porque estão fora de `task-manager-api/`:

- O repositório git é o diretório pai (`mba-ia-refactor-projects-skill`), e `code-smells-project/`, `ecommerce-api-legacy/`, `docs/` e `scripts/security_probes.sh` aparecem modificados/não versionados. Os mtimes são 12:11–12:12, antes do meu primeiro comando (o baseline subiu 12:20) — não são minhas alterações, mas vão junto se você commitar tudo de uma vez.
- Suas mudanças desta sessão estão isoladas em 20 arquivos de `task-manager-api/` + `src/middlewares/admin_guard.py` (novo).

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 17 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat .claude/skills/refactor-arch/references/project-analysis.md` |
| 2 | Bash | `cat requirements.txt && echo "=== README ===" && cat README.md && echo "=== .env.example ===" && cat .env.example && echo "=== .gitignore ===" && c...` |
| 3 | Bash | `for f in app.py seed.py src/app.py src/config/settings.py src/__init__.py src/config/__init__.py; do echo "=========== $f ==========="; cat -n "$f"...` |
| 4 | Bash | `for f in src/models/*.py; do echo "=========== $f ==========="; cat -n "$f"; done` |
| 5 | Bash | `for f in src/controllers/*.py src/controllers/validators/*.py; do echo "=========== $f ==========="; cat -n "$f"; done` |
| 6 | Bash | `for f in src/views/*.py src/services/*.py src/middlewares/*.py src/utils/*.py; do echo "=========== $f ==========="; cat -n "$f"; done` |
| 7 | Bash | `find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./__pycache__/*" \| sort \| xargs wc -l \| tail -5 && echo "--- e...` |
| 8 | Bash | `cat .claude/skills/refactor-arch/references/report-template.md` |
| 9 | Bash | `find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "*/__pycache__/*" \| sort \| xargs wc -l` |
| 10 | Bash | `cat .claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 11 | Bash | `SRC="app.py seed.py src" && echo "--- AP-01 secrets ---" && grep -rniE '(secret\|password\|passwd\|pwd\|api[_-]?key\|token\|private[_-]?key\|credential)\w...` |
| 12 | Bash | `SRC="app.py seed.py src" && echo "--- AP-15 exceptions ---" && grep -rnE 'except\s*:\|except Exception\|str\(e\)\|pass$' --include=*.py $SRC; echo "--...` |
| 13 | Bash | `for pkg in "flask 3.1.3" "flask-sqlalchemy 3.1.1" "flask-cors 6.0.5" "python-dotenv 1.2.3" "werkzeug 3.1.8" "itsdangerous 2.2.0"; do set -- $pkg; e...` |
| 14 | Bash | `echo "--- direct sqlalchemy imports ---" && grep -rn "^from sqlalchemy\\|^import sqlalchemy" --include=*.py app.py seed.py src && echo "--- venv ver...` |
| 15 | Bash | `echo "--- MAX_TAGS_LENGTH usage ---" && grep -rn "MAX_TAGS_LENGTH\\|MAX_DESCRIPTION_LENGTH\\|MAX_NAME_LENGTH\\|MAX_EMAIL_LENGTH\\|MAX_TITLE_LENGTH\\|COL...` |
| 16 | Bash | `echo "=== unused symbol check ===" && for sym in ensure_optional_text is_integer is_valid_email require_json_object calculate_percentage utcnow_nai...` |
| 17 | Bash | `cat -n requirements.txt && echo "--- sqlalchemy transitive audit ---" && for pkg in "sqlalchemy 2.0.54" "jinja2 3.1.6" "click 8.5.0" "blinker 1.9.0...` |

</details>

<details>
<summary>Fase 3 — 43 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat .claude/skills/refactor-arch/references/mvc-guidelines.md` |
| 2 | Bash | `cat .claude/skills/refactor-arch/references/validation-guide.md` |
| 3 | Bash | `sed -n '1,60p' .claude/skills/refactor-arch/references/refactoring-playbook.md && echo "..." && awk '/^## T-05\|^## T-06\|^## T-12\|^## T-13\|^## T-15\|...` |
| 4 | Bash | `awk '/^## T-05 /,/^## T-07 /' .claude/skills/refactor-arch/references/refactoring-playbook.md` |
| 5 | Bash | `awk '/^## T-12 /,/^## T-14 /' .claude/skills/refactor-arch/references/refactoring-playbook.md && awk '/^## T-15 /,/^## T-17 /' .claude/skills/refac...` |
| 6 | Bash | `export VALIDATION_DIR="${TMPDIR:-/tmp}/refactor-arch/task-manager-api" && mkdir -p "$VALIDATION_DIR" && echo "VALIDATION_DIR=$VALIDATION_DIR" && .v...` |
| 7 | Bash | `ls .venv/bin/ && echo "--- import check ---" && .venv/bin/python -c "import flask, flask_sqlalchemy, flask_cors, dotenv, werkzeug, itsdangerous, sq...` |
| 8 | Bash | `mkdir -p $TMP/refactor-arch/task-manager-api && cat > $TMP/refactor-arch/task-manager-api/smoke_test.py <<'PYEOF' """Smoke test reused unchanged fo...` |
| 9 | Bash | `V=$TMP/refactor-arch/task-manager-api && ls -la instance/ 2>/dev/null \|\| echo "no instance dir"; rm -f instance/tasks.db; .venv/bin/python seed.py ...` |
| 10 | Bash | `V=$TMP/refactor-arch/task-manager-api && .venv/bin/python "$V/smoke_test.py" http://127.0.0.1:5000 "$V/baseline.json" 2>&1 \| tail -60` |
| 11 | Bash | `V=$TMP/refactor-arch/task-manager-api && python3 -c " import json d=json.load(open('$V/baseline.json')) for c in d: if c['name'] in ('method.not.al...` |
| 12 | Bash | `cat > $TMP/refactor-arch/task-manager-api/log_leak_probe.py <<'PYEOF' """Força uma violação de chave única em users e mostra o que vai para o log...` |
| 13 | Bash | `V=$TMP/refactor-arch/task-manager-api && kill -- -"$(cat $V/server.pid)" 2>/dev/null; sleep 1; pkill -f "python app.py" 2>/dev/null; sleep 1; ss -l...` |
| 14 | Bash | `sleep 1; curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ 2>/dev/null; echo " <- 000 means stopped"; ps aux \| grep -c "[p]ython a...` |
| 15 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('src/config/settings.py') s = p.read_text() s = s.replace( "DEFAULT_LOG_LEVEL = 'INFO'\nTRUTHY_...` |
| 16 | Bash | `python3 - <<'PYEOF' import pathlib # --- models/database.py: opções de engine seguras + log sem parâmetros --- p = pathlib.Path('src/models/databas...` |
| 17 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('src/models/seed.py') s = p.read_text() s = s.replace( '"""Dados iniciais do projeto, usados pe...` |
| 18 | Bash | `cat > src/models/seed.py <<'PYEOF' """Dados iniciais do projeto, usados pelo script seed.py da raiz.""" import os import secrets from datetime im...` |
| 19 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('src/utils/validators.py') s = p.read_text() s = s.replace( "def is_valid_email(value) -> bool:...` |
| 20 | Bash | `python3 - <<'PYEOF' import pathlib # --- category_validator: reutiliza os helpers compartilhados e a mensagem do model --- p = pathlib.Path('src/co...` |
| 21 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('src/controllers/validators/task_validator.py') s = p.read_text() s = s.replace( "from src.mode...` |
| 22 | Bash | `python3 - <<'PYEOF' import pathlib # --- user_controller --- p = pathlib.Path('src/controllers/user_controller.py') s = p.read_text() s = s.replace...` |
| 23 | Bash | `cat > src/middlewares/admin_guard.py <<'PYEOF' """Guard dos endpoints destrutivos de administração — fechado por padrão. Enquanto a API não exige a...` |
| 24 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('src/app.py') s = p.read_text() s = s.replace("from src.models.database import init_database\n"...` |
| 25 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('.env.example') s = p.read_text() s = s.replace( "LOG_LEVEL=INFO\n", "LOG_LEVEL=INFO\n\n" "# En...` |
| 26 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path('README.md') s = p.read_text() s = s.replace( "A aplicação sobe em http://localhost:5000. O ...` |
| 27 | Bash | `V=$TMP/refactor-arch/task-manager-api && rm -f instance/tasks.db && .venv/bin/python seed.py 2>&1 \| tail -8 && echo "--- booting refactored ---" &&...` |
| 28 | Bash | `V=$TMP/refactor-arch/task-manager-api && .venv/bin/python "$V/smoke_test.py" http://127.0.0.1:5000 "$V/refactored.json" 2>&1 \| tail -55` |
| 29 | Bash | `cd $TMP/refactor-arch/task-manager-api && python3 - <<'PYEOF' import json base = json.load(open('baseline.json')) ref = json.load(open('refactored....` |
| 30 | Bash | `cd $TMP/refactor-arch/task-manager-api && python3 - <<'PYEOF' import json base = {c['name']: c for c in json.load(open('baseline.json'))} ref = {c[...` |
| 31 | Bash | `echo "--- error_handler.py alterado? ---" && git diff --stat src/middlewares/error_handler.py && echo "(vazio acima = intocado)" && echo && echo "-...` |
| 32 | Bash | `cd $TMP/refactor-arch/task-manager-api && cat > compare.py <<'PYEOF' """Compara baseline x refatorado. Allow é comparado como conjunto (Werkzeug o ...` |
| 33 | Bash | `echo "=== PROBE 1: campo de privilégio vindo de cliente anônimo ===" && curl -s -X POST http://127.0.0.1:5000/users -H 'Content-Type: application/j...` |
| 34 | Bash | `echo "=== PROBE 4: header Allow no 405 ===" && curl -s -i -X DELETE http://127.0.0.1:5000/health \| grep -iE "^HTTP\|^Allow" && echo && echo "=== PRO...` |
| 35 | Bash | `V=$TMP/refactor-arch/task-manager-api && echo "=== PROBE 2: endpoint destrutivo, com e sem configuração ===" && echo "-- a) sem nenhuma configuraçã...` |
| 36 | Bash | `S="app.py seed.py src" && echo "=== segredos/senhas literais ===" && grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"]...` |
| 37 | Bash | `.venv/bin/python - <<'PYEOF' import ast, pathlib problems = [] for path in sorted(pathlib.Path('.').glob('**/*.py')): if '.venv' in path.parts or '...` |
| 38 | Bash | `echo "=== _name agora delega ao helper compartilhado ===" && sed -n '16,19p' src/controllers/validators/category_validator.py && echo "---" && sed ...` |
| 39 | Bash | `pkill -f "python app.py"; sleep 2; echo "--- portas 5000/5001 ---"; (curl -s -m 2 -o /dev/null -w "5000: %{http_code}\n" http://127.0.0.1:5000/; cu...` |
| 40 | Bash | `curl -s -m 2 -o /dev/null -w "5000: %{http_code}\n" http://127.0.0.1:5000/ ; curl -s -m 2 -o /dev/null -w "5001: %{http_code}\n" http://127.0.0.1:5...` |
| 41 | Bash | `cd <repo> && git rev-parse --show-toplevel && echo "--- task-manager-api tem .git próprio? ---" && ls -d task-manager-api/.git 2>/dev/null \|\| echo ...` |
| 42 | Bash | `rm -rf instance && find . -path ./.venv -prune -o -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; echo "instance/: $(ls -d instance 2>/d...` |
| 43 | Bash | `find . -name "*.py" -not -path "./.venv/*" -not -path "./.claude/*" \| wc -l \| sed 's/^/arquivos .py: /' && find . -name "*.py" -not -path "./.venv/...` |

</details>
