# Reexecução da skill (v1.6.0) — Projeto 1: `code-smells-project` (Python/Flask)

Execução que produziu o código versionado do projeto 1. Parte da saída da v1.5.1 e usa a skill v1.6.0, em que a autenticação das rotas de gestão de um finding AP-06 (token assinado no login + guard por papel) passou a ser correção obrigatória (`mvc-guidelines.md` §9, exceção 11). Antes ela ia para "Remaining Items".

```bash
cd code-smells-project
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume eead10e7-c8e9-4b7d-a1ec-0578e23f05a4 --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 9 | 2.6 min | US$ 1.02 | 8 |
| Fase 3 (após `y`) | 26 | 4.5 min | US$ 2.55 | 25 |

## Fase 1 — saída

# refactor-arch — Fases 1 e 2 (somente leitura)

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (runtime local 3.14.7; nenhuma versão declarada no projeto)
Framework:     Flask 3.1.3
Dependencies:  flask-cors 6.0.5, werkzeug 3.1.8 (sqlite3, hmac, secrets da stdlib)
Domain:        API de E-commerce / Loja (produtos, usuarios, pedidos, itens_pedido, relatórios de vendas)
Architecture:  MVC em camadas — config/models/services/controllers/views/middlewares separados, create_app()
Source files:  35 files analyzed (8 empty __init__.py) (~1239 lines of code)
Database:      SQLite via sqlite3, SQL puro com placeholders (arquivo loja.db, DATABASE_PATH)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py → python app.py (port 5000; schema e seed criados automaticamente no primeiro boot)
Endpoints:     19 routes
  GET    /                            → sistema_controller.index (src/controllers/sistema_controller.py:24)
  GET    /health                      → sistema_controller.health_check (src/controllers/sistema_controller.py:29)
  POST   /admin/reset-db              → sistema_controller.reset_database [admin_only] (src/controllers/sistema_controller.py:44)
  POST   /admin/query                 → sistema_controller.executar_query [admin_only] (src/controllers/sistema_controller.py:50)
  GET    /produtos                    → produto_controller.listar_produtos (src/controllers/produto_controller.py:21)
  GET    /produtos/busca              → produto_controller.buscar_produtos (src/controllers/produto_controller.py:27)
  GET    /produtos/<id>               → produto_controller.buscar_produto (src/controllers/produto_controller.py:36)
  POST   /produtos                    → produto_controller.criar_produto (src/controllers/produto_controller.py:40)
  PUT    /produtos/<id>               → produto_controller.atualizar_produto (src/controllers/produto_controller.py:47)
  DELETE /produtos/<id>               → produto_controller.deletar_produto (src/controllers/produto_controller.py:54)
  GET    /usuarios                    → usuario_controller.listar_usuarios (src/controllers/usuario_controller.py:13)
  GET    /usuarios/<id>               → usuario_controller.buscar_usuario (src/controllers/usuario_controller.py:18)
  POST   /usuarios                    → usuario_controller.criar_usuario (src/controllers/usuario_controller.py:25)
  POST   /login                       → usuario_controller.login (src/controllers/usuario_controller.py:32)
  POST   /pedidos                     → pedido_controller.criar_pedido (src/controllers/pedido_controller.py:9)
  GET    /pedidos                     → pedido_controller.listar_todos_pedidos (src/controllers/pedido_controller.py:15)
  GET    /pedidos/usuario/<id>        → pedido_controller.listar_pedidos_usuario (src/controllers/pedido_controller.py:20)
  PUT    /pedidos/<id>/status         → pedido_controller.atualizar_status_pedido (src/controllers/pedido_controller.py:25)
  GET    /relatorios/vendas           → relatorio_controller.relatorio_vendas (src/controllers/relatorio_controller.py:6)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-1-rerun-v160.md`](../../reports/audit-project-1-rerun-v160.md). A mensagem terminou com:

```text
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Resposta enviada: `y`

## Fase 3 — saída

> Títulos rebaixados um nível para caber neste documento; conteúdo sem alterações.

## Fase 3 concluída — rotas de gestão exigem login

A falha crítica da auditoria (AP-06) foi corrigida:
- **Login:** agora devolve um token assinado.
- **Rotas de gestão:** as 9 rotas listadas exigem esse token e o papel certo.

Validei no app rodando:
- **Smoke test:** as 37 chamadas batem com o baseline.
- **Impactos:** cada cenário de risco da auditoria foi reproduzido e não acontece mais.

Nada foi commitado; as mudanças estão na working tree.

```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

### New Project Structure

```text
app.py                          # ponto de entrada (python app.py)
src/
├── app.py                      # create_app(): composition root (+ TOKEN_MAX_AGE)
├── config/settings.py          # settings do ambiente (+ TOKEN_MAX_AGE_SECONDS)
├── models/
│   ├── database.py             # conexão, transação, schema/seed (papéis via constantes)
│   ├── tipos_usuario.py        # NOVO — TIPO_ADMIN / TIPO_CLIENTE
│   ├── usuario_model.py        # TIPO_PADRAO = TIPO_CLIENTE
│   └── produto_model.py, pedido_model.py, relatorio_model.py, sistema_model.py
├── services/
│   ├── token_service.py        # NOVO — token de login assinado (itsdangerous + SECRET_KEY), só com o id
│   └── pedido_service.py, notificacao_service.py
├── controllers/                # usuario_controller.login() inclui o token
├── views/                      # rotas de gestão envolvidas por admin_required / owner_or_admin
│   └── serializers.py          # serializar_login(usuario, token)
├── middlewares/
│   ├── auth_guard.py           # NOVO — 401 sem token/token inválido, 403 sem papel; papel lido do banco
│   ├── admin_guard.py          # /admin/* (inalterado: fechado por padrão)
│   └── error_handler.py
└── utils/errors.py
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| Unprotected Management Endpoints — login issues no credential | CRITICAL | Fixed | T-06 | `src/services/token_service.py`, `src/middlewares/auth_guard.py`, `src/controllers/usuario_controller.py`, `src/views/serializers.py`, `src/views/{produto,usuario,pedido,relatorio}_routes.py` |
| Magic Strings — user roles | LOW | Fixed | T-15 | `src/models/tipos_usuario.py`, `src/models/database.py`, `src/models/usuario_model.py` |

### Contract Changes

- **`POST /login`**:
  - rota, status e campos iguais aos de antes;
  - `dados` ganha o campo `token`, assinado e com validade de 8 h, configurável em `TOKEN_MAX_AGE_SECONDS` (§9 exceção 11).
- **Exigem `Authorization: Bearer <token>` de um administrador**: `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`.
- **Exigem o token do próprio usuário ou de um administrador**: `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`.
- **Respostas das rotas guardadas:**
  - sem token, ou com token adulterado, expirado ou de um usuário que não existe mais: **401** `{"erro": "Autenticação necessária", "sucesso": false}`;
  - usuário sem permissão: **403**;
  - com o papel certo: resposta idêntica à original.
- **Continuam públicas:** vitrine (`GET /produtos*`), `POST /usuarios`, `POST /login`, `POST /pedidos`, `GET /`, `GET /health`.
- **Dependência:** `itsdangerous==2.2.0` foi fixada no `requirements.txt`. Ela já vinha instalada junto com o Flask e agora é importada diretamente; o PyPI não aponta vulnerabilidades.

### How to Run

```bash
pip install -r requirements.txt
export SECRET_KEY=<valor-aleatorio-longo> SEED_PASSWORD=<senha-dos-usuarios-demo>   # opcional, veja .env.example
python app.py                                                                          # http://127.0.0.1:5000
## token: POST /login {"email": "admin@loja.com", "senha": "<SEED_PASSWORD>"} → dados.token
```

### Validation

```text
  ✓ Application boots without errors (python app.py, port 5055 via PORT; 0 tracebacks in 5 boot logs)
  ✓ All endpoints respond correctly (37/37 checks match the baseline, 19/19 endpoints; 1 documented contract change: login gains "token")
  ✓ Guarded routes (9): 401 without token, with tampered token and with forged unsigned token; 403 with customer token; baseline response with admin token
  ✓ Owner access: customer reads /usuarios/3 and /pedidos/usuario/3 (own) → 200; another user's → 403
  ✓ Token carries only {"usuario_id": 1}; expired token (TOKEN_MAX_AGE_SECONDS=1, +2.5 s) → 401; token of a user removed by reset-db → 401
  ✓ Impact reproduced: anonymous PUT/DELETE /produtos twice → 401, price/stock of products 1 and 4 unchanged
  ✓ Impact reproduced: anonymous/customer cancel of order 1 twice → 401/403, status "pendente" and stock unchanged; admin cancel twice → stock 28→30 once
  ✓ Privilege field on sign-up ({"tipo":"admin","role":"admin"}) → user created as "cliente", gets 403 on /usuarios
  ✓ Duplicate e-mail write → 409; log contains no password hashes or passwords
  ✓ 405 on PATCH /produtos/1 keeps the Allow header
  ✓ /admin/* with no configuration → 403 (with and without X-Admin-Token)
  ✓ Public storefront routes still 200 without token
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-audit greps + pyflakes clean)
```

### Remaining Items

- None

```text
================================
```

Mais algumas coisas que você deve saber:
- **Pedidos:** `POST /pedidos` continua público, conforme a regra "o cliente faz o próprio pedido" (§9 exceção 11). Qualquer pessoa pode fazer um pedido em nome de outro `usuario_id`. Para fechar isso, seria preciso exigir que o dono do token seja o `usuario_id` do pedido, o que muda o contrato dessa rota. É uma decisão sua; não entra na auditoria.
- **Relatório de vendas:** `GET /relatorios/vendas` inclui os pedidos cancelados no faturamento. Isso não está no catálogo e deixei como estava, mas vale revisar.
- **`SECRET_KEY`:** se não for definida, os tokens deixam de valer a cada reinício e não funcionam entre vários workers. Defina essa variável em produção.
- **Limpeza:** todos os servidores foram parados e não sobrou banco nem `__pycache__` no projeto. Os artefatos da validação estão em `/tmp/refactor-arch/code-smells-project/run-2026-09-25/`.

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 8 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat .claude/skills/refactor-arch/references/project-analysis.md && cat .claude/skills/refactor-arch/references/report-template.md` |
| 2 | Bash | `cat requirements.txt .env.example README.md; for f in app.py $(find src -name '*.py' \| sort); do echo "=== $f"; cat -n $f; done; wc -l app.py $(find s...` |
| 3 | Read | `/home/diego/.claude/projects/-home-diego-projects-mba-mba-ia-refactor-projects-skill-code-smells-project/eead10e7-c8e9-4b7d-a1ec-0578e23f05a4/tool-res...` |
| 4 | Read | `/home/diego/.claude/projects/-home-diego-projects-mba-mba-ia-refactor-projects-skill-code-smells-project/eead10e7-c8e9-4b7d-a1ec-0578e23f05a4/tool-res...` |
| 5 | Bash | `cat .claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 6 | Bash | `awk '/^## 9/,0' .claude/skills/refactor-arch/references/mvc-guidelines.md` |
| 7 | Bash | `S="app.py src"; echo "--AP01"; grep -rniE '(secret\|password\|passwd\|pwd\|pass\|api[_-]?key\|token\|private[_-]?key\|credential)\w*["'"'"']?\s*[:=]\s*["'"'"'...` |
| 8 | Bash | `for p in flask/3.1.3 flask-cors/6.0.5 werkzeug/3.1.8; do echo "== $p"; curl -s --max-time 20 https://pypi.org/pypi/$p/json \| python3 -c 'import sys,js...` |

</details>

<details>
<summary>Fase 3 — 25 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch/references && cat validation-guide.md; echo ======; grep -n '^## \\|^### ' refactoring-playb...` |
| 2 | Bash | `sed -n 1,15p refactoring-playbook.md; sed -n 357,556p refactoring-playbook.md; sed -n 1028,1063p refactoring-playbook.md` |
| 3 | Bash | `cd <repo>/code-smells-project && git check-ignore -v loja.db .venv __pycache__ 2>&1; ls -a; V=$TMP/refactor-arch/code-smells-project; mkdir -p $V && p...` |
| 4 | Write | `$TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 5 | Bash | `ls -la $TMP/refactor-arch/code-smells-project/; head -20 $TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 6 | Bash | `mkdir -p $TMP/refactor-arch/code-smells-project/run-2026-09-25` |
| 7 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-25/smoke_test.py` |
| 8 | Bash | `R=$TMP/refactor-arch/code-smells-project/run-2026-09-25; V=$TMP/refactor-arch/code-smells-project/venv cat > $R/env.sh <<EOF export PORT=5055 DATABASE...` |
| 9 | Bash | `python3 - <<'EOF' import re,pathlib p=pathlib.Path("src/config/settings.py"); s=p.read_text() s=s.replace('PORTA_PADRAO = 5000\n','PORTA_PADRAO = 5000...` |
| 10 | Write | `<repo>/code-smells-project/src/models/tipos_usuario.py` |
| 11 | Bash | `python3 - <<'EOF' import pathlib p=pathlib.Path("src/models/database.py"); s=p.read_text() s=s.replace('from werkzeug.security import generate_passwor...` |
| 12 | Write | `<repo>/code-smells-project/src/services/token_service.py` |
| 13 | Bash | `python3 - <<'EOF' import pathlib p=pathlib.Path("src/controllers/usuario_controller.py"); s=p.read_text() s=s.replace('from src.models import usuario_...` |
| 14 | Write | `<repo>/code-smells-project/src/middlewares/auth_guard.py` |
| 15 | Bash | `python3 - <<'EOF' import pathlib def edit(path, pairs): p=pathlib.Path(path); s=p.read_text() for a,b in pairs: assert a in s, (path,a); s=s.replace(a...` |
| 16 | Bash | `cat > src/views/produto_routes.py <<'EOF' from flask import Blueprint from src.controllers import produto_controller as controller from src.middleware...` |
| 17 | Bash | `curl -s --max-time 20 https://pypi.org/pypi/itsdangerous/2.2.0/json \| python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["vulnerabilities"])...` |
| 18 | Bash | `R=$TMP/refactor-arch/code-smells-project/run-2026-09-25; V=$TMP/refactor-arch/code-smells-project/venv rm -f $R/loja-refactored.db ( . $R/env.sh $R/lo...` |
| 19 | Bash | `$TMP/refactor-arch/code-smells-project/venv/bin/python - <<'EOF' import json R="$TMP/refactor-arch/code-smells-project/run-2026-09-25" b=json.load(ope...` |
| 20 | Bash | `cd $TMP/refactor-arch/code-smells-project/run-2026-09-25 && B=http://127.0.0.1:5055; J='-H Content-Type:application/json' login(){ curl -s -X POST $B/...` |
| 21 | Bash | `R=$TMP/refactor-arch/code-smells-project/run-2026-09-25; V=$TMP/refactor-arch/code-smells-project/venv kill -- -"$(cat $R/server.pid)"; sleep 0.5; rm ...` |
| 22 | Bash | `B=http://127.0.0.1:5055; J='-H Content-Type:application/json'; R=$TMP/refactor-arch/code-smells-project/run-2026-09-25 st(){ curl -s -o /dev/null -w '...` |
| 23 | Bash | `R=$TMP/refactor-arch/code-smells-project/run-2026-09-25; V=$TMP/refactor-arch/code-smells-project/venv; B=http://127.0.0.1:5055; J='-H Content-Type:ap...` |
| 24 | Bash | `S="app.py src" echo "--secrets"; grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" $S echo "--debug"; gre...` |
| 25 | Bash | `ss -ltnp 2>/dev/null \| grep -c ':5055 '; git status --porcelain --ignored .; find . -name __pycache__ -not -path './.venv/*' -prune -print` |

</details>
