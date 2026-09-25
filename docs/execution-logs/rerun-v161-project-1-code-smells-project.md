# Reexecução da skill (v1.6.1) — Projeto 1: `code-smells-project` (Python/Flask)

Execução final, que produziu o código versionado do projeto. Parte da saída de a v1.6.0 (login com token e rotas de gestão com papel) e usa a skill v1.6.1. Nessa versão, a autenticação das rotas de gestão de um finding AP-06 é correção obrigatória (`mvc-guidelines.md` §9, exceção 11), e isso inclui as ações feitas em nome de um usuário. Principal resultado: `POST /pedidos` passou a exigir o token do próprio usuário (ou de um admin), fechando o pedido em nome de terceiros.

```bash
cd code-smells-project
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume ef2691b5-8d95-4728-80d1-ec11a8170b1e --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 12 | 3.1 min | US$ 1.25 | 11 |
| Fase 3 (após `y`) | 16 | 3.0 min | US$ 2.28 | 15 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3 (.venv local: CPython 3.12.13)
Framework:     Flask 3.1.3
Dependencies:  flask-cors 6.0.5, itsdangerous 2.2.0, werkzeug 3.1.8 (todas importadas no código)
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido, relatórios de vendas)
Architecture:  MVC em camadas — views só registram rotas, controllers orquestram, models concentram SQL, config vem do ambiente
Source files:  38 files analyzed (~1349 lines of code; 8 empty __init__.py)
Database:      SQLite via sqlite3, SQL puro com placeholders (arquivo loja.db, configurável por DATABASE_PATH)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py → python app.py (port 5000, host 127.0.0.1; schema + seed automáticos no primeiro boot)
Endpoints:     19 routes
  GET    /                            → sistema_controller.index (src/views/sistema_routes.py:8)
  GET    /health                      → sistema_controller.health_check (src/views/sistema_routes.py:9)
  POST   /admin/reset-db              → sistema_controller.reset_database [admin_only] (src/views/sistema_routes.py:10)
  POST   /admin/query                 → sistema_controller.executar_query [admin_only] (src/views/sistema_routes.py:11)
  GET    /produtos                    → produto_controller.listar_produtos (src/views/produto_routes.py:9)
  GET    /produtos/busca              → produto_controller.buscar_produtos (src/views/produto_routes.py:10)
  GET    /produtos/<id>               → produto_controller.buscar_produto (src/views/produto_routes.py:11)
  POST   /produtos                    → produto_controller.criar_produto [admin] (src/views/produto_routes.py:14)
  PUT    /produtos/<id>               → produto_controller.atualizar_produto [admin] (src/views/produto_routes.py:15)
  DELETE /produtos/<id>               → produto_controller.deletar_produto [admin] (src/views/produto_routes.py:18)
  GET    /usuarios                    → usuario_controller.listar_usuarios [admin] (src/views/usuario_routes.py:8)
  GET    /usuarios/<id>               → usuario_controller.buscar_usuario [dono/admin] (src/views/usuario_routes.py:9)
  POST   /usuarios                    → usuario_controller.criar_usuario (src/views/usuario_routes.py:13)
  POST   /login                       → usuario_controller.login (src/views/usuario_routes.py:14)
  POST   /pedidos                     → pedido_controller.criar_pedido (src/views/pedido_routes.py:8)
  GET    /pedidos                     → pedido_controller.listar_todos_pedidos [admin] (src/views/pedido_routes.py:9)
  GET    /pedidos/usuario/<id>        → pedido_controller.listar_pedidos_usuario [dono/admin] (src/views/pedido_routes.py:12)
  PUT    /pedidos/<id>/status         → pedido_controller.atualizar_status_pedido [admin] (src/views/pedido_routes.py:16)
  GET    /relatorios/vendas           → relatorio_controller.relatorio_vendas [admin] (src/views/relatorio_routes.py:8)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-1-rerun-v161.md`](../../reports/audit-project-1-rerun-v161.md). A mensagem terminou com:

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
app.py                          # ponto de entrada (python app.py) — inalterado
src/
├── app.py                      # create_app(): composition root
├── config/settings.py          # settings a partir de variáveis de ambiente
├── models/
│   ├── database.py             # conexão, transações, schema (default de status via constante) e seed
│   ├── status_pedido.py        # NOVO: status de pedido e estados finais (sem import circular)
│   ├── tipos_usuario.py        # papéis de usuário
│   ├── pedido_model.py         # pedidos/itens, estoque (importa status_pedido)
│   ├── produto_model.py, usuario_model.py, relatorio_model.py, sistema_model.py
├── services/                   # pedido_service, notificacao_service, token_service
├── controllers/
│   ├── pedido_controller.py    # criar_pedido confere dono do usuario_id (exigir_dono_ou_admin)
│   ├── sistema_controller.py   # ENDPOINTS_INDICE (renomeado)
│   └── produto/usuario/relatorio_controller.py, validators.py
├── views/                      # blueprints (POST /pedidos agora com login_required), serializers, converters
├── middlewares/
│   ├── auth_guard.py           # + login_required, + exigir_dono_ou_admin (reusado por owner_or_admin)
│   ├── admin_guard.py, error_handler.py
└── utils/errors.py
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| Broken Authentication — pedido criado em nome de qualquer usuário | HIGH | Fixed | T-06 | `src/middlewares/auth_guard.py`, `src/views/pedido_routes.py`, `src/controllers/pedido_controller.py`, `README.md` |
| Poor Naming | LOW | Fixed | T-15 | `src/controllers/sistema_controller.py` |
| Magic Strings | LOW | Fixed | T-15 | `src/models/status_pedido.py`, `src/models/database.py`, `src/models/pedido_model.py`, `src/models/relatorio_model.py`, `src/services/notificacao_service.py` |
| Dead Code and Redundant Calls | LOW | Partially fixed | T-16 | `src/middlewares/auth_guard.py`, `src/controllers/pedido_controller.py` |

### Contract Changes

- `POST /pedidos` agora exige `Authorization: Bearer <token>` (mvc-guidelines §9, exceção 11, "Acting on behalf of a user"):
  - sem token ou com token adulterado/expirado → `401`;
  - token de um cliente com `usuario_id` de outro usuário → `403` (`{"erro": "Acesso negado", "sucesso": false}`);
  - token do próprio usuário ou de um admin → `201` com o mesmo envelope de antes.
  - A tabela de acesso do README foi atualizada.

### How to Run

```bash
pip install -r requirements.txt
export SECRET_KEY=<valor-aleatório-longo> SEED_PASSWORD=<senha-dos-usuarios-demo>
python app.py            # http://127.0.0.1:5000
## token para as rotas protegidas e para POST /pedidos:
curl -s -X POST http://127.0.0.1:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","senha":"<SEED_PASSWORD>"}'
```

### Validation

```text
  ✓ Application boots without errors (python app.py, port 5055 via PORT; sem traceback no log)
  ✓ All endpoints respond correctly (30/30 checks match the baseline; 19/19 rotas do inventário; o header Allow do 405 tem os mesmos métodos, só em outra ordem, que já varia na app original)
  ✓ IDOR reproduzido na app original (anônimo, token adulterado e joao→maria: 201, estoque 30→24) e bloqueado após a correção (401/401/403, estoque inalterado, repetição também 401)
  ✓ Dono cria pedido para si (201) e admin cria para outro usuário (201); payload inválido continua 400
  ✓ Rotas de gestão: 401 sem token, 401 com token adulterado, 403 com token de não-admin; o login devolve o token
  ✓ Cadastro com {"tipo": "admin"} por cliente anônimo → usuário criado como "cliente"
  ✓ /admin/query e /admin/reset-db sem configuração → 403
  ✓ E-mail duplicado → 409, e o log não contém hashes de senha nem traceback
  ✓ Cancelar pedido devolve o estoque uma única vez (22→25, repetido 25); sair de "cancelado" → 400
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-audit)
```

### Remaining Items

- **Dead Code and Redundant Calls:** a parte de `g.usuario` foi resolvida, porque `g.usuario` agora é lido por `exigir_dono_ou_admin()`. A outra parte da minha recomendação, remover `configure_logging()` de `app.py:11`, estava errada e não foi aplicada: `load_settings()` roda antes de `create_app()` e pode registrar o aviso de `SECRET_KEY` ausente, então a chamada é necessária para esse aviso sair formatado. Não há o que corrigir aí.

```text
================================
```

O smoke test, os probes e os logs ficaram em `/tmp/refactor-arch/code-smells-project/`. Não sobrou servidor rodando nem arquivo gerado dentro do projeto. As alterações não foram commitadas.

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 11 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch/references && cat project-analysis.md report-template.md` |
| 2 | Bash | `cd <repo>/code-smells-project && cat .claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 3 | Bash | `cat requirements.txt .env.example README.md && git status --short . && git log --oneline -3 && find . -type f -not -path './.git/*' -not -path './.cla...` |
| 4 | Bash | `wc -l README.md && sed -n 1,400p README.md \| head -150; git status --short . ; find . -type f -not -path './.git/*' -not -path './.claude/*' \| sort; w...` |
| 5 | Bash | `git check-ignore -v .venv loja.db; for f in app.py src/app.py src/config/settings.py src/models/*.py src/services/*.py src/utils/errors.py; do echo "=...` |
| 6 | Read | `/home/diego/.claude/projects/-home-diego-projects-mba-mba-ia-refactor-projects-skill-code-smells-project/ef2691b5-8d95-4728-80d1-ec11a8170b1e/tool-res...` |
| 7 | Bash | `for f in src/controllers/*.py src/views/*.py src/middlewares/*.py; do echo "=== $f"; cat -n "$f"; done` |
| 8 | Bash | `grep -n "^## \\|^### " .claude/skills/refactor-arch/references/mvc-guidelines.md; awk '/^## 9/,0' .claude/skills/refactor-arch/references/mvc-guideline...` |
| 9 | Bash | `S="app.py src"; echo "--- g.usuario"; grep -rn "g\.usuario\\|\bg\b" $S --include=*.py \| grep -v "^.*import"; echo "--- print/global/except"; grep -rnE ...` |
| 10 | Bash | `for p in flask/3.1.3 flask-cors/6.0.5 itsdangerous/2.2.0 werkzeug/3.1.8; do echo "== $p"; curl -s --max-time 20 https://pypi.org/pypi/$p/json \| python...` |
| 11 | Bash | `grep -n "POST /pedidos\\|Público" README.md` |

</details>

<details>
<summary>Fase 3 — 15 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch/references && cat validation-guide.md; grep -n "^## \\|^### " refactoring-playbook.md` |
| 2 | Bash | `sed -n 1,43p refactoring-playbook.md; sed -n 431,556p refactoring-playbook.md` |
| 3 | Bash | `mkdir -p $TMP/refactor-arch/code-smells-project && cat > $TMP/refactor-arch/code-smells-project/smoke_test.py <<'EOF' import json, sys, urllib.request...` |
| 4 | Bash | `ss -ltnp \| grep 5055; pgrep -af "python -B app.py"` |
| 5 | Bash | `kill -- -$(ps -o pgid= 2013743 \| tr -d ' ') ; sleep 0.5; ss -ltnp \| grep 5055 \|\| echo livre cd $TMP/refactor-arch/code-smells-project && sed -i 's\|^ki...` |
| 6 | Bash | `cd $TMP/refactor-arch/code-smells-project && cat > probes.py <<'EOF' import json, sys, urllib.request, urllib.error BASE = sys.argv[1]; SENHA = "senha...` |
| 7 | Bash | `python3 - <<'EOF' from pathlib import Path p = Path("src/middlewares/auth_guard.py"); s = p.read_text() s = s.replace('''def admin_required(view):''',...` |
| 8 | Bash | `git checkout -- app.py && git diff src/` |
| 9 | Bash | `cat > src/models/status_pedido.py <<'EOF' """Status dos pedidos. Módulo próprio para o schema e os models usarem sem import circular.""" STATUS_PENDEN...` |
| 10 | Bash | `python3 - <<'EOF' from pathlib import Path p = Path("README.md"); s = p.read_text() def rep(old, new): global s; assert s.count(old) == 1, old; s = s....` |
| 11 | Bash | `cd $TMP/refactor-arch/code-smells-project && ./run2.sh refactored smoke_test.py 2>&1 \| grep -v Terminado; python3 - <<'EOF' import json b = json.load(...` |
| 12 | Bash | `V=$TMP/refactor-arch/code-smells-project; rm -f $V/loja-default.db; DATABASE_PATH=$V/loja-default.db SEED_PASSWORD=senha-seed-123 PORT=5055 setsid .ve...` |
| 13 | Bash | `ss -ltnp \| grep 5055 \|\| echo "porta livre"; echo "hash/traceback no log: $(grep -ciE 'scrypt:\|pbkdf2:\|Traceback' $TMP/refactor-arch/code-smells-projec...` |
| 14 | Bash | `echo "--- segredos"; grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" --include=*.py src/ app.py; echo "...` |
| 15 | Bash | `git status --porcelain --ignored . ; find . -name __pycache__ -not -path './.venv/*'; ls *.db 2>/dev/null; pgrep -f "app.py" \| xargs -r ps -o pid,cmd ...` |

</details>
