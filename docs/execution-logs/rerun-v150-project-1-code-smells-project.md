# Reexecução da skill (v1.5.0) — Projeto 1: `code-smells-project` (Python/Flask)

Execução com a skill v1.5.0, que acrescenta ao playbook a "Rule zero" (um finding só fecha quando a consequência descrita no **Impact** deixa de acontecer — mover o código de camada não basta) e a transformação T-19 (implementar o comportamento anunciado e não executado). Motivo: a avaliação apontou que o `audit-project-1.md` registrava "cancelar o pedido não devolve o estoque", mas a refatoração só levou o `print` para `notificacao_service`, que continuava apenas logando `"Devolver estoque."`.

Como na execução v1.4.0, a Fase 1 analisa o **código já refatorado**.

> **Execução descartada.** Esta rodada fechou com 403 listagens e CRUD do domínio (`GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `DELETE /produtos/<id>`…), contrariando o requisito de que os endpoints originais continuem respondendo. A skill foi ajustada (v1.5.1) e a execução que vale está em [`rerun-v151-project-1-code-smells-project.md`](rerun-v151-project-1-code-smells-project.md).

```bash
cd code-smells-project
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume 21cc7aba-873f-4a13-b7a2-a3c441f690d9 --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 11 | 3.1 min | US$ 1.07 | 10 |
| Fase 3 (após `y`) | 43 | 6.6 min | US$ 3.30 | 42 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (runtime não declarado; `str | None` em settings.py exige ≥ 3.10; local 3.14.7)
Framework:     Flask 3.1.3
Dependencies:  flask-cors 6.0.5, werkzeug 3.1.8
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido, relatórios de vendas)
Architecture:  MVC em camadas — views só registram rotas, controllers orquestram, models com SQL parametrizado, config via env
Source files:  34 files analyzed (8 empty __init__.py) (~1169 lines of code)
Database:      SQLite via sqlite3 (raw SQL) (arquivo loja.db, configurável por DATABASE_PATH; schema + seed em src/models/database.py)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py → python app.py (port 5000, host 127.0.0.1)
Endpoints:     19 routes
  GET    /produtos                      → listar_produtos (src/controllers/produto_controller.py:21)
  GET    /produtos/busca                → buscar_produtos (src/controllers/produto_controller.py:27)
  GET    /produtos/<int:produto_id>     → buscar_produto (src/controllers/produto_controller.py:36)
  POST   /produtos                      → criar_produto (src/controllers/produto_controller.py:40)
  PUT    /produtos/<int:produto_id>     → atualizar_produto (src/controllers/produto_controller.py:47)
  DELETE /produtos/<int:produto_id>     → deletar_produto (src/controllers/produto_controller.py:54)
  GET    /usuarios                      → listar_usuarios (src/controllers/usuario_controller.py:13)
  GET    /usuarios/<int:usuario_id>     → buscar_usuario (src/controllers/usuario_controller.py:18)
  POST   /usuarios                      → criar_usuario (src/controllers/usuario_controller.py:25)
  POST   /login                         → login (src/controllers/usuario_controller.py:32)
  POST   /pedidos                       → criar_pedido (src/controllers/pedido_controller.py:9)
  GET    /pedidos                       → listar_todos_pedidos (src/controllers/pedido_controller.py:15)
  GET    /pedidos/usuario/<int:usuario_id> → listar_pedidos_usuario (src/controllers/pedido_controller.py:20)
  PUT    /pedidos/<int:pedido_id>/status → atualizar_status_pedido (src/controllers/pedido_controller.py:25)
  GET    /relatorios/vendas             → relatorio_vendas (src/controllers/relatorio_controller.py:6)
  GET    /                              → index (src/controllers/sistema_controller.py:24)
  GET    /health                        → health_check (src/controllers/sistema_controller.py:29)
  POST   /admin/reset-db                → reset_database (src/controllers/sistema_controller.py:44) [admin_only]
  POST   /admin/query                   → executar_query (src/controllers/sistema_controller.py:50) [admin_only]
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-1-rerun-v150.md`](../../reports/audit-project-1-rerun-v150.md). O finding que motivou esta iteração agora aparece com nome próprio — `[HIGH] Announced-but-missing Behavior — cancelling an order does not restore stock` (AP-07) — e a Recommendation descreve o comportamento a implementar (transação, tabela de transições, devolução exatamente uma vez), não só a camada. A mensagem terminou com:

```text
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Resposta enviada: `y`

## Fase 3 — saída

> Títulos rebaixados um nível para caber neste documento; conteúdo sem alterações. O `scripts/security_probes.sh` citado no primeiro parágrafo fica fora do projeto: eu o editei em paralelo (novas provas de estoque), e a skill corretamente não mexeu nele.

Cleanup is done: no server is listening on the port, no `.db` files are in the project, and `__pycache__` was removed. `git status` also shows `scripts/security_probes.sh` as modified. That file is outside this project, I never touched it, and the tree was clean when the session started, so something else changed it in the meantime. I left it alone.

```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

### New Project Structure

```text
app.py                          # ponto de entrada (python app.py)
requirements.txt                # + itsdangerous==2.2.0 (já vinha com o Flask; agora importado direto)
src/
├── app.py                      # create_app(): config, CORS, conversor int limitado, blueprints, error handler, banco
├── config/settings.py          # env vars; padrões nomeados; CORS padrão = http://HOST:PORT; TOKEN_MAX_AGE
├── models/
│   ├── database.py             # conexão por request, transaction(), SQLITE_INT_MAX, schema/seed (nomes em inglês)
│   ├── pedido_model.py         # criação transacional + atualizar_status com estados finais e devolução de estoque
│   ├── produto_model.py
│   ├── relatorio_model.py
│   ├── sistema_model.py        # /admin/query com authorizer do SQLite (só leitura; credenciais viram NULL)
│   └── usuario_model.py        # + TIPO_ADMIN
├── services/
│   ├── notificacao_service.py
│   ├── pedido_service.py       # notifica só quando o status mudou de fato (após o commit)
│   └── token_service.py        # NOVO: emite/valida token de login assinado com SECRET_KEY
├── controllers/                # login devolve o token; validators com inteiros limitados ao SQLite
├── views/
│   ├── converters.py           # NOVO: <int:...> limitado a 2^63-1 (id enorme → 404, não 500)
│   ├── serializers.py          # serializar_login inclui "token"
│   └── *_routes.py             # rotas com dados de terceiros/destrutivas envolvidas por admin_required / owner_or_admin
├── middlewares/
│   ├── auth_guard.py           # NOVO: admin_required, owner_or_admin (Bearer token; 403 por padrão)
│   ├── admin_guard.py          # /admin/* (flag + X-Admin-Token)
│   └── error_handler.py
└── utils/errors.py
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| Unprotected Destructive Endpoints and Missing Authentication | CRITICAL | Partially fixed | T-06 | `src/services/token_service.py`, `src/middlewares/auth_guard.py`, `src/views/*_routes.py`, `src/controllers/usuario_controller.py` |
| Sensitive Data Exposure — credential columns readable via /admin/query | CRITICAL | Fixed | T-05 | `src/models/sistema_model.py` |
| Announced-but-missing Behavior — cancelling an order does not restore stock | HIGH | Fixed | T-19, T-09 | `src/models/pedido_model.py`, `src/services/pedido_service.py`, `src/services/notificacao_service.py` |
| Missing Input Validation — unbounded integers crash with 500 | MEDIUM | Fixed | T-12 | `src/controllers/validators.py`, `src/views/converters.py`, `src/app.py` |
| Dead Configuration — SECRET_KEY never used | LOW | Fixed | T-16 | `src/services/token_service.py` (a chave agora assina os tokens) |
| Magic Strings — inline config defaults and CORS origin tied to port 5000 | LOW | Fixed | T-15 | `src/config/settings.py` |
| Poor Naming — mixed languages for the same concepts | LOW | Fixed | T-15 | `src/config/settings.py`, `src/models/database.py`, `src/middlewares/*.py`, `src/utils/errors.py` (convenção documentada no README) |

### Contract Changes

- `POST /login`: `dados` ganhou o campo `token`. É uma adição; os campos existentes não mudaram.
- `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `DELETE /produtos/<id>`: sem o token de um usuário `admin`, respondem `403` com o envelope de erro (§9-2: dados de terceiros e remoção). Com o token, as respostas são iguais ao baseline.
- `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`: só o próprio usuário ou um admin; os demais recebem `403` (§9-2).
- `PUT /pedidos/<id>/status`, o que muda (§9-10 e §9-6):
  - cancelar agora devolve o estoque, uma única vez;
  - sair de `cancelado` ou de `entregue` responde `400`;
  - repetir o status atual responde `200` e não altera nada.
- Inteiros acima de 2^63−1: `500 → 400` no corpo (`POST /produtos`, `POST /pedidos`) e `500 → 404` na URL (§9-3).
- `POST /admin/query` (só com admin habilitado): colunas de credenciais saem como `null` em consultas que as renomeiam (§9-2). Comandos fora de SELECT/READ/FUNCTION são negados.

### How to Run

```bash
pip install -r requirements.txt
export SECRET_KEY=<valor-aleatório-longo>      # recomendado: sem ele, os tokens de login morrem a cada reinício
export SEED_PASSWORD=<senha-dos-usuários-demo> # opcional; admin@loja.com é o admin de demonstração
python app.py                                  # http://127.0.0.1:5000
## rotas restritas: POST /login → use dados.token em "Authorization: Bearer <token>"
```

### Validation

```text
  ✓ Application boots without errors (python app.py, port 5057 via PORT; 0 tracebacks nos logs refatorados)
  ✓ All endpoints respond correctly — 19/19 rotas exercitadas; config padrão: 40/53 checks idênticos ao baseline,
    13 diferenças todas documentadas (6× anônimo→403, 4× 500→400/404, 2× login com "token",
    1× DELETE /produtos/11 [admin] 404→200 porque o delete anônimo anterior foi bloqueado)
  ✓ Config com admin habilitado: 39/53 idênticos; as mesmas 13 diferenças + a ordem do header Allow no 405 (mesmo conjunto de métodos)
  ✓ Bypass `VALUES ... UNION ALL SELECT * FROM usuarios` em /admin/query: baseline devolvia hash scrypt, agora column4 = null
  ✓ Cancelamento: estoque 30 → 26 (pedido) → 30 (cancelar) → 30 (cancelar de novo); reabrir cancelado → 400; entregue → pendente → 400
  ✓ Anônimo com {"tipo": "admin"} no cadastro → gravado como cliente
  ✓ Endpoints protegidos sem configuração/token → 403; cliente → 403; dono → 200; admin → 200
  ✓ Token com payload trocado (usuario_id=1) e token inválido → 403
  ✓ Ids e valores > 2^63−1 → 404/400, sem OverflowError no log
  ✓ Header Allow presente no 405
  ✓ Logs sem hashes nem senhas (grep scrypt/pbkdf2/senhas de teste = 0; e-mail duplicado → 409 da aplicação, sem erro do driver)
  ✓ Re-audit: nenhum segredo literal, debug fixo, SQL interpolado com entrada, acesso a dados em controllers/views ou API deprecada; pyflakes limpo
  ✗ Zero CRITICAL/HIGH anti-patterns remaining — AP-06 fica parcial (ver abaixo)
```

### Remaining Items

- **AP-06 (parcial)**:
  - **Corrigido:** o login emite token assinado, a chave não é previsível, a escalada de privilégio pelo cadastro está bloqueada, e as rotas com dados de terceiros e a remoção de produtos ficam fechadas por padrão.
  - **Ainda público**, porque exigir autenticação transformaria um `200` legítimo em `401/403` fora das exceções do §9:
    - `POST /produtos` e `PUT /produtos/<id>` (qualquer um altera catálogo, preço e estoque);
    - `PUT /pedidos/<id>/status` (qualquer um aprova ou cancela pedidos alheios);
    - `POST /pedidos` com `usuario_id` arbitrário (pedido em nome de outra pessoa).
  - **Recomendação:** aplicar `admin_required` às escritas de produto e à troca de status, e no `POST /pedidos` tirar o `usuario_id` do token (`owner_or_admin`). Os guards já estão prontos; isso só depende de você aprovar a mudança de contrato.
- **SECRET_KEY em produção:** sem a variável, a chave é efêmera e os tokens deixam de valer a cada reinício ou worker. O boot emite um aviso, mas vale tornar a variável obrigatória no deploy.
- Artefatos de validação (baseline, logs, sondas): `/tmp/refactor-arch/code-smells-project/run-2026-09-23/`.

```text
================================
```

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 10 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch && cat references/project-analysis.md references/report-template.md` |
| 2 | Bash | `cd <repo>/code-smells-project && cat -n requirements.txt .env.example README.md app.py && find src -name '*.py' \| xargs wc -l \| sort -n \| tail -40` |
| 3 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch && cat references/anti-patterns-catalog.md` |
| 4 | Bash | `cd <repo>/code-smells-project && for f in src/app.py src/config/settings.py src/models/*.py src/utils/errors.py src/middlewares/*.py; do echo "=== $f"...` |
| 5 | Bash | `cd <repo>/code-smells-project && for f in src/services/*.py src/controllers/*.py src/views/*.py; do echo "=== $f"; cat -n $f; done` |
| 6 | Read | `/home/diego/.claude/projects/-home-diego-projects-mba-mba-ia-refactor-projects-skill-code-smells-project/21cc7aba-873f-4a13-b7a2-a3c441f690d9/tool-res...` |
| 7 | Bash | `grep -rniE 'print\(\|console\.\|utcnow\|before_first_request\|pkg_resources\|__version__\|global \|except:\|pass$\|TODO\|FIXME\|devolv\|restor\|refund\|reembols\|ses...` |
| 8 | Bash | `for p in flask/3.1.3 flask-cors/6.0.5 werkzeug/3.1.8; do echo "== $p"; curl -s --max-time 20 https://pypi.org/pypi/$p/json \| python3 -c 'import sys,js...` |
| 9 | Bash | `cd /tmp && python3 - <<'EOF' import sqlite3, re c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row c.execute("CREATE TABLE usuarios (id INTE...` |
| 10 | Bash | `cd .claude/skills/refactor-arch && grep -n '^## ' references/mvc-guidelines.md; awk '/^## 9/,0' references/mvc-guidelines.md \| head -60` |

</details>

<details>
<summary>Fase 3 — 42 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd .claude/skills/refactor-arch && cat references/validation-guide.md; grep -n '^## \\|^### ' references/refactoring-playbook.md` |
| 2 | Bash | `cd .claude/skills/refactor-arch && sed -n 1,43p references/refactoring-playbook.md; sed -n 357,457p references/refactoring-playbook.md; sed -n 1088,12...` |
| 3 | Bash | `cd <repo>/code-smells-project && pwd && cat .gitignore 2>/dev/null; git check-ignore -v loja.db .venv __pycache__; ls -a; sed -n 5,15p .claude/skills/...` |
| 4 | Bash | `.venv/bin/python --version && .venv/bin/pip install -q -r requirements.txt && .venv/bin/pip list 2>/dev/null \| grep -iE 'flask\|werkzeug\|itsdangerous';...` |
| 5 | Bash | `ls .venv/bin; .venv/bin/python -c "import flask, flask_cors, werkzeug, itsdangerous; print(flask.__file__)" 2>&1; which uv` |
| 6 | Bash | `uv pip install --python .venv/bin/python -r requirements.txt 2>&1 \| tail -3; uv pip list --python .venv/bin/python 2>/dev/null \| grep -iE 'flask\|werkz...` |
| 7 | Write | `$TMP/refactor-arch/code-smells-project/smoke_test.py` |
| 8 | Bash | `ls -la $TMP/refactor-arch/code-smells-project/` |
| 9 | Bash | `mkdir -p $TMP/refactor-arch/code-smells-project/run-2026-09-23 && echo ok` |
| 10 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23/smoke_test.py` |
| 11 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23/run.sh` |
| 12 | Bash | `cd $TMP/refactor-arch/code-smells-project/run-2026-09-23 && bash run.sh baseline && bash run.sh baseline-admin admin \| tail -12` |
| 13 | Bash | `cd $TMP/refactor-arch/code-smells-project/run-2026-09-23 && python3 -c " import json;r=json.load(open('baseline-admin.json'));print(json.dumps(r[49]['...` |
| 14 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23/probe_cancel.py` |
| 15 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23/serve.sh` |
| 16 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23; bash $V/serve.sh probe-baseline && python3 $V/probe_cancel.py http://127.0.0.1:5057; kill -- ...` |
| 17 | Write | `<repo>/code-smells-project/src/config/settings.py` |
| 18 | Bash | `python3 - <<'EOF' import re p = "src/models/database.py" s = open(p).read() s = s.replace('''DatabaseError = sqlite3.Error ''', '''DatabaseError = sql...` |
| 19 | Edit | `<repo>/code-smells-project/src/models/pedido_model.py` |
| 20 | Edit | `<repo>/code-smells-project/src/models/pedido_model.py` |
| 21 | Edit | `<repo>/code-smells-project/src/services/pedido_service.py` |
| 22 | Edit | `<repo>/code-smells-project/src/services/notificacao_service.py` |
| 23 | Bash | `python3 - <<'EOF' p = "src/models/sistema_model.py" s = open(p).read() s = s.replace('''import logging import re ''', '''import logging import re impo...` |
| 24 | Bash | `grep -rn '\.mensagem\\|MENSAGENS_HTTP\\|ERRO_INTERNO\\|HEADER_TOKEN\\|_resposta' src app.py` |
| 25 | Write | `<repo>/code-smells-project/src/middlewares/error_handler.py` |
| 26 | Bash | `sed -i 's/ def __init__(self, mensagem):/ def __init__(self, message):/; s/ super().__init__(mensagem)/ super().__init__(message)/; s/ self.mensagem =...` |
| 27 | Write | `<repo>/code-smells-project/src/services/token_service.py` |
| 28 | Write | `<repo>/code-smells-project/src/middlewares/auth_guard.py` |
| 29 | Write | `<repo>/code-smells-project/src/middlewares/admin_guard.py` |
| 30 | Bash | `python3 - <<'EOF' def sub(p, a, b): s = open(p).read(); assert a in s, (p, a); open(p, "w").write(s.replace(a, b)) sub("src/models/usuario_model.py", ...` |
| 31 | Bash | `python3 - <<'EOF' def sub(p, a, b): s = open(p).read(); assert a in s, (p, a); open(p, "w").write(s.replace(a, b)) p = "src/controllers/validators.py"...` |
| 32 | Write | `<repo>/code-smells-project/src/views/converters.py` |
| 33 | Bash | `python3 - <<'EOF' def sub(p, a, b): s = open(p).read(); assert a in s, (p, a); open(p, "w").write(s.replace(a, b)) p = "src/app.py" sub(p, "from src.m...` |
| 34 | Bash | `grep -q itsdangerous requirements.txt \|\| echo "itsdangerous==2.2.0" >> requirements.txt; cat requirements.txt; curl -s https://pypi.org/pypi/itsdanger...` |
| 35 | Bash | `python3 - <<'EOF' def sub(p, a, b): s = open(p).read(); assert a in s, (p, a); open(p, "w").write(s.replace(a, b)) sub("src/views/produto_routes.py", ...` |
| 36 | Bash | `python3 - <<'EOF' def sub(p, a, b): s = open(p).read(); assert a in s, (p, a); open(p, "w").write(s.replace(a, b)) sub(".env.example", '''# Chave de a...` |
| 37 | Bash | `cd $TMP/refactor-arch/code-smells-project/run-2026-09-23 && bash run.sh refactored >/dev/null && bash run.sh refactored-admin admin > /dev/null; pytho...` |
| 38 | Bash | `cd $TMP/refactor-arch/code-smells-project/run-2026-09-23 && bash run.sh refactored-admin admin > /dev/null; python3 - <<'EOF' import json B, R = json....` |
| 39 | Write | `$TMP/refactor-arch/code-smells-project/run-2026-09-23/probe_auth.py` |
| 40 | Bash | `V=$TMP/refactor-arch/code-smells-project/run-2026-09-23; bash $V/serve.sh probe-refactored && python3 $V/probe_cancel.py http://127.0.0.1:5057 && echo...` |
| 41 | Bash | `echo "== secrets"; grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" --include=*.py src app.py; echo "== ...` |
| 42 | Bash | `ss -ltnp 2>/dev/null \| grep 5057; git status --porcelain --ignored; find . -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +; ls *.db ...` |

</details>
