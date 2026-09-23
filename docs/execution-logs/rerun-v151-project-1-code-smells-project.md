# Reexecução da skill (v1.5.1) — Projeto 1: `code-smells-project` (Python/Flask)

Execução que produziu o código versionado do projeto 1. Parte da saída da v1.4.0 (o código foi restaurado do commit `0dc0dc8`) e usa a skill v1.5.1:
- **v1.5.0:** "Rule zero" do playbook (o finding só fecha quando o Impact deixa de acontecer) e T-19 (comportamento anunciado e não executado).
- **v1.5.1:** a exceção 2 das guidelines passa a valer só para rotas administrativas por natureza. A execução v1.5.0 ([log](rerun-v150-project-1-code-smells-project.md)) tinha fechado com 403 listagens e CRUD do domínio.

```bash
cd code-smells-project
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume 162126e3-47e8-46d2-9908-12d32db4445b --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 12 | 3.7 min | US$ 1.30 | 11 |
| Fase 3 (após `y`) | 30 | 4.5 min | US$ 2.90 | 29 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (runtime não declarado; local: 3.14.7)
Framework:     Flask 3.1.3
Dependencies:  flask-cors 6.0.5, werkzeug 3.1.8
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido, relatórios de vendas)
Architecture:  MVC em camadas — config, models, services, controllers, views e middlewares separados; composition root em create_app()
Source files:  34 files analyzed (~1170 lines of code; 8 empty __init__.py)
Database:      SQLite via sqlite3 (raw SQL com placeholders) (arquivo loja.db, DATABASE_PATH)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py → python app.py (port 5000)
Endpoints:     19 routes
  GET    /                            → index (src/controllers/sistema_controller.py:24)
  GET    /health                      → health_check (src/controllers/sistema_controller.py:29)
  POST   /admin/reset-db              → reset_database [admin_only] (src/controllers/sistema_controller.py:44)
  POST   /admin/query                 → executar_query [admin_only] (src/controllers/sistema_controller.py:50)
  GET    /produtos                    → listar_produtos (src/controllers/produto_controller.py:21)
  GET    /produtos/busca              → buscar_produtos (src/controllers/produto_controller.py:27)
  GET    /produtos/<int:produto_id>   → buscar_produto (src/controllers/produto_controller.py:36)
  POST   /produtos                    → criar_produto (src/controllers/produto_controller.py:40)
  PUT    /produtos/<int:produto_id>   → atualizar_produto (src/controllers/produto_controller.py:47)
  DELETE /produtos/<int:produto_id>   → deletar_produto (src/controllers/produto_controller.py:54)
  GET    /usuarios                    → listar_usuarios (src/controllers/usuario_controller.py:13)
  GET    /usuarios/<int:usuario_id>   → buscar_usuario (src/controllers/usuario_controller.py:18)
  POST   /usuarios                    → criar_usuario (src/controllers/usuario_controller.py:25)
  POST   /login                       → login (src/controllers/usuario_controller.py:32)
  POST   /pedidos                     → criar_pedido (src/controllers/pedido_controller.py:9)
  GET    /pedidos                     → listar_todos_pedidos (src/controllers/pedido_controller.py:15)
  GET    /pedidos/usuario/<int:usuario_id> → listar_pedidos_usuario (src/controllers/pedido_controller.py:20)
  PUT    /pedidos/<int:pedido_id>/status   → atualizar_status_pedido (src/controllers/pedido_controller.py:25)
  GET    /relatorios/vendas           → relatorio_vendas (src/controllers/relatorio_controller.py:6)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-1-rerun-v151.md`](../../reports/audit-project-1-rerun-v151.md). A mensagem terminou com:

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

```text
app.py                          # ponto de entrada: python app.py
src/
├── app.py                      # create_app(): composition root (config, CORS, conversor de URL, blueprints, erros, banco)
├── config/settings.py          # settings via env; HOST_PADRAO/PORTA_PADRAO; origem CORS padrão derivada de host:porta
├── models/
│   ├── database.py             # conexão por request (g), transaction(), schema, seed
│   ├── produto_model.py
│   ├── usuario_model.py
│   ├── pedido_model.py         # atualizar_status: estados finais + devolução de estoque exatamente uma vez
│   ├── relatorio_model.py
│   └── sistema_model.py        # /admin/query: SELECT único, conexão read-only + authorizer que anula credenciais
├── services/
│   ├── pedido_service.py       # notifica só quando o status realmente mudou
│   └── notificacao_service.py
├── controllers/
│   ├── validators.py           # + faixa de inteiros de 64 bits (INTEIRO_MINIMO/INTEIRO_MAXIMO)
│   └── produto_/usuario_/pedido_/relatorio_/sistema_controller.py
├── views/
│   ├── converters.py           # NOVO: IdConverter — <int:...> limitado a 2^63-1 (acima disso → 404)
│   ├── serializers.py
│   └── *_routes.py             # blueprints: URL → controller
├── middlewares/
│   ├── error_handler.py
│   └── admin_guard.py
└── utils/errors.py
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| Sensitive Data Exposure — bypass do filtro de credenciais em /admin/query | CRITICAL | Fixed | T-05 | `src/models/sistema_model.py` (`_autorizar_leitura` + `set_authorizer`) |
| Unprotected Endpoints and Broken Authentication — rotas de domínio sem autenticação | CRITICAL | Not fixed | T-06 (bloqueado) | — (ver Remaining Items) |
| Business Logic — cancelamento anuncia devolução de estoque que não acontece | HIGH | Fixed | T-19, T-09 | `src/models/pedido_model.py`, `src/services/pedido_service.py`, `src/services/notificacao_service.py` |
| Missing Input Validation — inteiros fora da faixa do SQLite causam 500 | MEDIUM | Fixed | T-12 | `src/controllers/validators.py`, `src/views/converters.py`, `src/app.py` |
| Magic Strings — padrões de host/porta duplicados no CORS | LOW | Fixed | T-15 | `src/config/settings.py` |

### Contract Changes

- `PUT /pedidos/<id>/status`: mudar para `cancelado` agora devolve ao estoque as quantidades dos itens, na mesma transação e uma única vez (exceção 10). `cancelado` e `entregue` passam a ser estados finais: sair deles responde 400 (`"Pedido cancelado não pode mudar de status"`). Repetir o status atual responde 200 sem alterar nada e sem notificar (exceções 6/10).
- `GET/PUT/DELETE /produtos/<id>`, `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`, `PUT /pedidos/<id>/status`: ids acima de 2^63-1 respondem 404, antes 500 (exceção 3).
- `POST /produtos`, `PUT /produtos/<id>`, `POST /pedidos`: inteiros fora da faixa de 64 bits (e `preco` como `10**400`) respondem 400 `"<Campo> fora do intervalo permitido"`, antes 500 (exceção 3).
- `POST /admin/query` (só com flag + token): colunas de credenciais voltam `NULL` ou são removidas mesmo via `UNION`/alias/subconsulta (exceção 2).
- Config: sem `CORS_ORIGINS`, a origem liberada passa a ser `http://<HOST>:<PORT>`. Com os padrões, o valor é o mesmo de antes (`http://127.0.0.1:5000`).

### How to Run

```bash
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000
## opcionais: SEED_PASSWORD=..., HOST, PORT, CORS_ORIGINS,
##            ADMIN_ENDPOINTS_ENABLED=true + ADMIN_TOKEN=... para /admin/*
```

### Validation

```text
  ✓ Application boots without errors (python app.py, port 5000; Python 3.12.13, 0 tracebacks no log)
  ✓ All endpoints respond correctly (53/53 checks cobrindo as 19 rotas; 47 idênticos ao baseline, 5 mudanças documentadas 500→404/400, 1 difere só na ordem dos métodos no Allow)
  ✓ 405 mantém o header Allow (GET, HEAD, OPTIONS, POST — mesmo conjunto do baseline)
  ✓ Probe de privilégio: POST /usuarios com "tipo":"admin" → usuário criado com tipo "cliente" (não há endpoint de update de usuário)
  ✓ Probe sem configuração: POST /admin/query e /admin/reset-db → 403
  ✓ Probe de log: nenhum hash de senha (scrypt:) nos logs; e-mail duplicado → 409 tratado, sem erro do driver
  ✓ Probe AP-07: estoque 30/15 → pedido 25/14 → cancelar 30/15 → cancelar de novo 30/15 (sem devolução dupla) → reabrir 400; entregue→cancelado 400 (baseline: ficava 25/14 e aceitava tudo)
  ✓ Probe AP-04: "SELECT 1,2,3,4,5,6 UNION ALL SELECT * FROM usuarios" → nenhum hash nas linhas (baseline: vazava o hash); DELETE → 400
  ✓ Probe AP-14: 5 entradas fora da faixa → 404/400, 0 tracebacks (baseline: 5×500)
  ✓ Probe AP-20: PORT=8080 → cors_origins = ['http://127.0.0.1:8080']
  ✗ Zero CRITICAL/HIGH anti-patterns remaining (re-audit) — AP-06 (CRITICAL) continua aberto, ver Remaining Items
```

### Remaining Items

- **AP-06 — rotas de domínio sem autenticação (Not fixed).** Qualquer anônimo ainda pode apagar e alterar produtos, mudar o status de pedidos alheios, listar todos os pedidos e usuários (PII) e ler o relatório de vendas. Para corrigir, o `/login` precisa emitir um token assinado (`itsdangerous`, que já vem com o Flask) e as rotas precisam de guards de admin e de dono do recurso. Isso transforma um 200 legítimo em 401/403, e mvc-guidelines §9 não permite isso sem pedido explícito ("Not allowed without asking the user"). A parte que dá para corrigir sem autenticação já estava correta antes desta execução: `tipo` não é aceito de clientes anônimos. Se quiser essa mudança, peça "incluir autenticação" e eu implemento como uma quebra de contrato documentada.

```text
================================
```

Observações:
- As mudanças não foram commitadas: 9 arquivos modificados, mais o novo `src/views/converters.py`.
- O commit mais recente (`5b9cb43`) tinha revertido o código do projeto para o estado anterior à correção de estoque do `af1d790`. Esta execução reimplementou essa correção e a do `/admin/query` de forma mais enxuta, sem o esquema de token que o `af1d790` havia adicionado.
- Os artefatos de validação estão fora do projeto, em `/tmp/refactor-arch/code-smells-project/run-2026-09-23-b/`.

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 11 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat .claude/skills/refactor-arch/references/project-analysis.md .claude/skills/refactor-arch/references/report-template.md` |
| 2 | Bash | `cat README.md requirements.txt .env.example; for f in app.py $(find src -name '*.py' \| sort); do echo "=== $f"; cat -n $f; done; wc -l app.py $(find s...` |
| 3 | Read | `/home/diego/.claude/projects/-home-diego-projects-mba-mba-ia-refactor-projects-skill-code-smells-project/162126e3-47e8-46d2-9908-12d32db4445b/tool-res...` |
| 4 | Bash | `cat .claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 5 | Bash | `git log --oneline -5 -- . ; git show --stat af1d790 \| head -20; grep -rniE '(devolv\|restor\|refund\|reembols\|releas\|liber\|revog\|revok\|TODO\|FIXME)' --inc...` |
| 6 | Bash | `git show --stat --format='%h %s' af1d790 5b9cb43 \| grep -v '^$'` |
| 7 | Bash | `for p in flask/3.1.3 flask-cors/6.0.5 werkzeug/3.1.8; do echo "== $p"; curl -s --max-time 20 https://pypi.org/pypi/$p/json \| python3 -c 'import sys,js...` |
| 8 | Bash | `G="grep -rniE --include=*.py"; echo "--AP01"; $G '(secret\|password\|passwd\|pwd\|pass\|api[_-]?key\|token\|private[_-]?key\|credential)\w*["'"'"']?\s*[:=]\s*...` |
| 9 | Bash | `git log --diff-filter=A --format='%h %s' -- models.py database.py app.py \| tail -3; first=$(git log --diff-filter=A --format=%h -- app.py \| tail -1); ...` |
| 10 | Bash | `grep -n '' .claude/skills/refactor-arch/references/mvc-guidelines.md \| sed -n '/Contract preservation/,$p'` |
| 11 | Bash | `python3 - <<'EOF' import sqlite3, math, re, ast, pathlib c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row c.execute("CREATE TABLE usuarios...` |

</details>

<details>
<summary>Fase 3 — 29 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat .claude/skills/refactor-arch/references/validation-guide.md; grep -n '^## \\|^### ' .claude/skills/refactor-arch/references/refactoring-playbook.md` |
| 2 | Bash | `P=.claude/skills/refactor-arch/references/refactoring-playbook.md; sed -n '1,43p' $P; sed -n '324,356p;794,851p;929,964p;1088,1200p' $P` |
| 3 | Bash | `V=$TMP/refactor-arch/code-smells-project; mkdir -p $V && .venv/bin/python --version && .venv/bin/pip install -q -r requirements.txt && .venv/bin/pip f...` |
| 4 | Bash | `ls .venv/bin \| head; .venv/bin/python -m pip --version 2>&1; .venv/bin/python -c 'import flask, flask_cors, werkzeug; from importlib.metadata import v...` |
| 5 | Write | `$TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 6 | Bash | `V=$TMP/refactor-arch/code-smells-project; rm -f loja.db; SEED_PASSWORD=senha-demo-123 setsid .venv/bin/python app.py > $V/server-baseline.log 2>&1 < /...` |
| 7 | Bash | `V=$TMP/refactor-arch/code-smells-project; cat $V/server-baseline.log \| tail -5; ss -ltnp \| grep 5000; ls -la $V` |
| 8 | Bash | `kill 1256381; sleep 1; ss -ltnp \| grep 5000; sed -n '1,80p' $TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 9 | Bash | `sed -n '80,200p' $TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 10 | Bash | `B=$TMP/refactor-arch/code-smells-project; V=$B/run-2026-09-23-b; mkdir -p $V && python3 - "$B/smoke_test.py" "$V/smoke_test.py" <<'EOF' import sys src...` |
| 11 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23-b/probes.py` |
| 12 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b run() { # $1 = label, $2.. env label=$1; shift; rm -f loja.db env "$@" setsid .venv/bin/pyth...` |
| 13 | Bash | `ss -ltnp \| grep ':5000 '; pgrep -af 'app.py'` |
| 14 | Bash | `kill 1256779; V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b; cat > $V/srv.sh <<'EOF' # uso: source srv.sh; start <label> [VAR=valor...]; s...` |
| 15 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b; cat $V/server.pid; ps -o pid,pgid,cmd -C python \| grep app.py; ss -ltnp \| grep ':5000 '` |
| 16 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b; kill -- -1256926; sed -i 's\|^stop() .*\|stop() { pid=$(ss -ltnpH "sport = :5000" \\| grep -o ...` |
| 17 | Bash | `python3 - <<'EOF' p = "src/config/settings.py" s = open(p).read() s = s.replace('''NIVEL_LOG_PADRAO = "INFO" # Origens liberadas por padrão: apenas a ...` |
| 18 | Edit | `<repo>/code-smells-project/src/models/pedido_model.py` |
| 19 | Edit | `<repo>/code-smells-project/src/models/pedido_model.py` |
| 20 | Edit | `<repo>/code-smells-project/src/services/pedido_service.py` |
| 21 | Edit | `<repo>/code-smells-project/src/services/notificacao_service.py` |
| 22 | Bash | `python3 - <<'EOF' p = "src/models/sistema_model.py" s = open(p).read() s = s.replace('''import logging import re from src.models.database''', '''impor...` |
| 23 | Bash | `python3 - <<'EOF' p = "src/controllers/validators.py" s = open(p).read() def rep(a, b): global s assert s.count(a) == 1, a s = s.replace(a, b) rep('''...` |
| 24 | Bash | `python3 - <<'EOF' p = "src/app.py" s = open(p).read() s = s.replace('''from src.models.database import init_database ''', '''from src.models.database ...` |
| 25 | Bash | `python3 - <<'EOF' p = "README.md" s = open(p).read() def rep(a, b): global s assert s.count(a) == 1, a s = s.replace(a, b) rep("\| `CORS_ORIGINS` \| `ht...` |
| 26 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b; source $V/srv.sh start refactored && $P/.venv/bin/python $V/smoke_test.py http://127.0.0.1:...` |
| 27 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23-b; python3 - $V <<'EOF' import json, sys V = sys.argv[1] for f in ("baseline", "refactored"): ...` |
| 28 | Bash | `grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" --include=*.py src app.py; grep -rnE "debug\s*=\s*True"...` |
| 29 | Bash | `find src -name __pycache__ -type d -exec rm -rf {} +; rm -f loja.db; ss -ltn \| grep ':5000 ' \|\| echo "porta 5000 livre"; pgrep -af 'python app.py' \| g...` |

</details>
