# Reexecução da skill (v1.4.0) — Projeto 1: `code-smells-project` (Python/Flask)

Execução com a skill v1.4.0, que fecha o padrão sistêmico identificado na varredura finding-a-finding (guard fechado por padrão, headers do framework no contrato, sem segredo em log/seed).

Diferente das execuções de `docs/execution-logs/project-1-*.md`, aqui a Fase 1 analisa o **código já refatorado** — por isso a arquitetura detectada é "MVC em camadas" e os achados são o que sobrou.

```bash
cd code-smells-project
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume f8bd9da6-7fc3-4b34-b0fc-5cf7fda9cc4e --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 16 | 5.2 min | US$ 1.68 | 15 |
| Fase 3 (após `y`) | 38 | 10.1 min | US$ 6.14 | 37 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python [sem pin de runtime no projeto; Python 3.14.7 instalado — src/config/settings.py:39 usa `str | None` (3.10+)]
Framework:     Flask 3.1.3 (requirements.txt:1)
Dependencies:  Flask-CORS 6.0.5, Werkzeug 3.1.8 (requirements.txt:2-3)
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido, relatório de vendas)
Architecture:  Layered MVC — config/models/services/controllers/views/middlewares com app factory em src/app.py
Source files:  34 files analyzed (~1082 lines of code, 8 __init__.py vazios)
Database:      SQLite via driver sqlite3 (raw SQL parametrizado, arquivo DATABASE_PATH, padrão `loja.db`)
DB tables:     produtos, usuarios, pedidos, itens_pedido (src/models/database.py:11-44)
Entry point:   app.py → `python app.py` (port 5000, HOST/PORT via env; schema e seed criados no boot por init_database)
Endpoints:     19 routes
  GET    /                              → index (src/views/sistema_routes.py:8)
  GET    /health                        → health_check (src/views/sistema_routes.py:9)
  POST   /admin/reset-db                → reset_database (src/views/sistema_routes.py:10)
  POST   /admin/query                   → executar_query (src/views/sistema_routes.py:11)
  GET    /produtos                      → listar_produtos (src/views/produto_routes.py:7)
  GET    /produtos/busca                → buscar_produtos (src/views/produto_routes.py:8)
  GET    /produtos/<int:produto_id>     → buscar_produto (src/views/produto_routes.py:9)
  POST   /produtos                      → criar_produto (src/views/produto_routes.py:10)
  PUT    /produtos/<int:produto_id>     → atualizar_produto (src/views/produto_routes.py:11)
  DELETE /produtos/<int:produto_id>     → deletar_produto (src/views/produto_routes.py:12)
  GET    /usuarios                      → listar_usuarios (src/views/usuario_routes.py:7)
  GET    /usuarios/<int:usuario_id>     → buscar_usuario (src/views/usuario_routes.py:8)
  POST   /usuarios                      → criar_usuario (src/views/usuario_routes.py:9)
  POST   /login                         → login (src/views/usuario_routes.py:10)
  POST   /pedidos                       → criar_pedido (src/views/pedido_routes.py:7)
  GET    /pedidos                       → listar_todos_pedidos (src/views/pedido_routes.py:8)
  GET    /pedidos/usuario/<int:usuario_id> → listar_pedidos_usuario (src/views/pedido_routes.py:9-11)
  PUT    /pedidos/<int:pedido_id>/status   → atualizar_status_pedido (src/views/pedido_routes.py:12-14)
  GET    /relatorios/vendas             → relatorio_vendas (src/views/relatorio_routes.py:7)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-1-rerun.md`](../../reports/audit-project-1-rerun.md). A mensagem terminou com:

```text
O relatório mostra a árvore limpa (nenhuma alteração não commitada), então não é necessário backup antes de prosseguir.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Resposta enviada: `y`

## Fase 3 — saída

> Títulos rebaixados um nível para caber neste documento; conteúdo sem alterações.

Cleanup done, no servers running, no artifacts left in the project. Final report:

```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

### New Project Structure

A arquitetura já era MVC em camadas (Fase 1), então — conforme `mvc-guidelines.md` §10, "Already MVC: only fix the audit findings in place" — nenhum arquivo foi criado, movido ou removido. A estrutura abaixo é a final; os 12 arquivos alterados estão marcados.

```text
code-smells-project/
├── app.py                          # (*) ponto de entrada: configure_logging() + create_app() + app.run()
├── requirements.txt                #     flask 3.1.3, flask-cors 6.0.5, werkzeug 3.1.8 (inalterado)
├── .env.example                    # (*) + SEED_PASSWORD, LOG_LEVEL; CORS_ORIGINS com padrão fechado
├── README.md                       # (*) seed sem senha fixa, novos env vars, limites do /admin/query
└── src/
    ├── app.py                      # (*) composition root: configura logging e injeta SEED_PASSWORD
    ├── config/
    │   └── settings.py             # (*) configure_logging(); CORS padrão fechado; seed_password
    ├── models/
    │   ├── database.py             # (*) seed sem senha no código (env ou sorteada e logada uma vez)
    │   ├── produto_model.py        # (*) existência do produto verificada dentro da transação
    │   ├── usuario_model.py        #     hash scrypt + upgrade de senha legada (inalterado)
    │   ├── pedido_model.py         #     BEGIN IMMEDIATE, baixa de estoque atômica (inalterado)
    │   ├── relatorio_model.py      #     agregação em uma query + faixas de desconto (inalterado)
    │   └── sistema_model.py        # (*) /admin/query não devolve mais colunas de credenciais
    ├── services/
    │   ├── pedido_service.py       #     caso de uso pedido + notificação (inalterado)
    │   └── notificacao_service.py  #     efeitos externos simulados via logger (inalterado)
    ├── controllers/
    │   ├── validators.py           # (*) política de senha e limites de tamanho no cadastro
    │   ├── produto_controller.py   # (*) reusa a constante de mensagem do model
    │   ├── sistema_controller.py   # (*) índice derivado do url_map via url_for
    │   ├── usuario_controller.py   #     (inalterado)
    │   ├── pedido_controller.py    #     (inalterado)
    │   └── relatorio_controller.py #     (inalterado)
    ├── views/
    │   ├── *_routes.py             #     blueprints: só URL → controller (inalterado)
    │   └── serializers.py          #     allowlist de campos públicos (inalterado)
    ├── middlewares/
    │   ├── error_handler.py        # (*) preserva os headers da HTTPException (Allow no 405)
    │   └── admin_guard.py          #     guard fechado por padrão + hmac.compare_digest (inalterado)
    └── utils/
        └── errors.py               #     hierarquia AppError → status HTTP (inalterado)
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| AP-04 Sensitive data exposure — credenciais de demonstração semeadas por padrão | HIGH | Fixed | T-05 | `src/models/database.py:66-72`, `src/models/database.py:111-123`, `src/config/settings.py:68`, `src/app.py:26` |
| AP-10 Insecure runtime configuration — CORS liberado para qualquer origem por padrão | MEDIUM | Fixed | T-01 | `src/config/settings.py:15`, `src/config/settings.py:66` |
| AP-11 Non-atomic multi-step writes — verificação de existência fora da transação | MEDIUM | Fixed | T-09 | `src/models/produto_model.py:67-77`, `src/models/produto_model.py:80-90` |
| AP-19 Inadequate middleware usage — handler central descarta headers do framework | MEDIUM | Partially fixed | T-07 | `src/middlewares/error_handler.py:24-34`, `src/middlewares/error_handler.py:42-44` |
| AP-14 Missing or inconsistent input validation — cadastro sem política de senha | MEDIUM | Fixed | T-12 | `src/controllers/validators.py:11-15`, `src/controllers/validators.py:81-90` |
| AP-04 Sensitive data exposure — `/admin/query` lê a coluna de senhas | MEDIUM | Fixed | T-05, T-06 | `src/models/sistema_model.py:12-15`, `src/models/sistema_model.py:43-51`, `src/models/sistema_model.py:60` |
| AP-23 print/console logging — logging configurado só no caminho `python app.py` | LOW | Fixed | T-16 | `src/config/settings.py:18-25`, `src/app.py:16`, `app.py:11` |
| AP-16 Duplicated code — tabela de rotas replicada no handler do índice | LOW | Fixed | T-13 | `src/controllers/sistema_controller.py:12-21`, `src/controllers/sistema_controller.py:24-26` |
| AP-22 Dead code — coluna `ativo` nunca escrita nem filtrada | LOW | Not fixed | T-16 | — (bloqueado pelo contrato, ver Remaining Items) |

### Contract Changes

- **POST /login** — `admin@loja.com` / `admin123` agora responde **401** (era 200). Os usuários de demonstração não têm mais senha no código: ela vem de `SEED_PASSWORD` ou é sorteada no primeiro boot e registrada no log uma única vez (§9 exceção 8). Login continua funcionando normalmente com qualquer conta cadastrada.
- **POST /usuarios** — senha com menos de 8 caracteres agora responde **400** com `{"erro": "Senha deve ter no mínimo 8 caracteres", "sucesso": false}` (era 201). Também passam a ser rejeitados `nome` > 200 e `email` > 254 caracteres. O `POST /login` **não** aplica mínimos, para não travar contas já existentes.
- **405 Method Not Allowed** — a resposta voltou a incluir o header `Allow` (ex.: `Allow: OPTIONS, HEAD, POST, GET` em `DELETE /produtos`), que o handler central descartava. Corpo, status e `Content-Type: application/json` seguem idênticos. É restauração de header exigida por §9, não uma mudança de contrato desejada.
- **POST /admin/query** — consulta que cita `senha`/`password`/`token`/`secret` responde **400** (era 200 devolvendo os hashes scrypt); `SELECT *` em `usuarios` continua 200, mas sem o campo `senha` nas linhas (§9 exceções 1 e 2).
- **CORS** — o padrão de `CORS_ORIGINS` passou de `*` para `http://127.0.0.1:5000`. Para liberar outras origens, defina a variável explicitamente (`CORS_ORIGINS=*` reproduz o comportamento antigo).

Rotas, métodos, nomes de campos de requisição/resposta, códigos de sucesso, porta e comando de start permanecem inalterados.

### How to Run

```bash
pip install -r requirements.txt
python app.py                     # http://127.0.0.1:5000

# Senha dos usuários de demonstração: escolha a sua...
SEED_PASSWORD=uma-senha-forte python app.py
# ...ou deixe em branco e leia a senha sorteada no log ("SEED_PASSWORD não definido; ... senha XXXX")

# Endpoints administrativos (desabilitados por padrão)
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=um-token-aleatorio python app.py

# Outras variáveis: SECRET_KEY, HOST, PORT, FLASK_DEBUG, APP_ENV, LOG_LEVEL,
# DATABASE_PATH, SEED_DATABASE, CORS_ORIGINS — veja .env.example
```

### Validation

Ambiente: Python 3.12.13 em `.venv` (git-ignored), flask 3.1.3 / flask-cors 6.0.5 / werkzeug 3.1.8 conforme `requirements.txt`. Mesmo ambiente e mesmo script de smoke test nas duas execuções.

```text
  ✓ Application boots without errors (python app.py, port 5000) — log sem traceback nas duas execuções
  ✓ All endpoints respond correctly (43/47 checks match the baseline; 4 diferenças = mudanças de contrato documentadas, 0 regressões)
  ✓ Os 19 endpoints do inventário da Fase 1 exercitados (47 checks: happy path, not-found, payload inválido, 405, probes)
  ✓ PROBE escalação de privilégio no create: POST /usuarios {"tipo":"admin","is_admin":true} → usuário criado com tipo "cliente"
  ✓ PROBE endpoint destrutivo sem configuração: POST /admin/reset-db e POST /admin/query → 403 (não 200)
  ✓ PROBE erro forçado em escrita (email duplicado → 409): log sem hash scrypt, sem senha e sem parâmetros ligados (0 ocorrências)
  ✓ PROBE header decorado pelo framework: DELETE /produtos → 405 com "Allow: OPTIONS, HEAD, POST, GET"
  ✓ PROBE /admin/query com token válido: "SELECT email, senha FROM usuarios" → 400; "SELECT * FROM usuarios" → 200 sem o campo senha
       (no baseline as duas devolviam 200 com os hashes scrypt completos)
  ✓ PROBE corrida de escrita: produto_model.atualizar/deletar de id inexistente levantam NotFoundError dentro da transação
  ✓ PROBE CORS: requisição com Origin externa não recebe Access-Control-Allow-Origin
  ✓ Re-auditoria: sem acesso a dados em controllers/views, sem APIs depreciadas, sem print(), sem imports não usados,
       sem credenciais no código, sem DeprecationWarning em runtime, .env.example presente
  ✓ Auditoria de dependências (PyPI): flask 3.1.3, flask-cors 6.0.5, werkzeug 3.1.8 sem vulnerabilidades conhecidas
  ✗ Zero CRITICAL/HIGH anti-patterns remaining (re-audit) — nenhum CRITICAL ou HIGH restante (AP-04 HIGH foi fechado),
       marcado ✗ porque 2 itens seguem abertos: 1 MEDIUM parcial (AP-19) e 1 LOW (AP-22), ambos abaixo em Remaining Items
```

Os 4 hits de `execute(f"...")` que sobraram na re-auditoria (`src/models/produto_model.py:29,34`, `src/models/usuario_model.py:16`, `src/models/pedido_model.py:24`) foram reverificados: interpolam apenas listas de colunas constantes e a string de placeholders `?, ?, ?` — nenhum dado de requisição entra no SQL. Não são findings (AP-02, "Not a finding when placeholders are used and only constant fragments are concatenated").

### Remaining Items

- **AP-19, parte não corrigida — envelope de erro do `/health`.** O header `Allow` foi restaurado, mas `health_check` (`src/controllers/sistema_controller.py:28-33`) continua montando `{"status": "erro", "detalhes": "Banco de dados indisponível"}` em vez do envelope `{"erro": ..., "sucesso": false}` do resto da API. Minha recomendação da Fase 2 era unificar; não apliquei porque `mvc-guidelines.md` §9 lista "changing response envelopes" como mudança que precisa da sua autorização. **Recomendação:** trocar o corpo desse caminho de erro 500 para o envelope padrão — posso aplicar se você autorizar.
- **AP-22, não corrigido — coluna `ativo`.** As duas opções que recomendei esbarram em §9: remover o campo do schema/serializer altera os campos de resposta de todos os endpoints de produto, e implementar soft delete transformaria o `409 Conflict` de `DELETE /produtos/<id>` (produto com pedidos) em `200`, quebrando um status de erro que o original tratava. **Recomendação:** resolver numa mudança versionada da API — soft delete com `409` preservado ou remoção do campo num `/v2`.
- **Observação fora do escopo da auditoria: a API não tem autenticação alguma.** `PUT /pedidos/<id>/status` permite que qualquer cliente anônimo altere o status de qualquer pedido, e `GET /usuarios` expõe a lista de e-mails. Isso não foi reportado como finding na Fase 2 e não pode ser corrigido dentro das exceções de §9 (tornar rotas públicas em autenticadas precisa da sua decisão). **Recomendação:** introduzir sessão/token nas rotas de escrita de pedido e nas de leitura de usuários.
- **Nota sobre o repositório:** o `git status` é do repositório pai (`mba-ia-refactor-projects-skill`) e mostra arquivos modificados em `ecommerce-api-legacy/` — projeto irmão que eu **não** toquei. Minhas alterações são exatamente os 12 arquivos sob `code-smells-project/` do diffstat acima (130 inserções, 31 remoções). Vale conferir de onde vieram as mudanças do outro diretório antes de commitar.

```text
================================
```

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 15 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat <repo>/code-smells-project/.claude/skills/refactor-arch/references/project-analysis.md` |
| 2 | Bash | `cat requirements.txt && echo "=== README ===" && cat README.md && echo "=== .env.example ===" && cat .env.example && echo "=== app.py (root) ===" &...` |
| 3 | Bash | `for f in src/app.py src/__init__.py src/config/__init__.py src/config/settings.py src/models/__init__.py src/models/database.py; do echo "===== $f ...` |
| 4 | Bash | `for f in src/models/produto_model.py src/models/usuario_model.py src/models/pedido_model.py src/models/relatorio_model.py src/models/sistema_model....` |
| 5 | Bash | `for f in src/controllers/__init__.py src/controllers/validators.py src/controllers/produto_controller.py src/controllers/usuario_controller.py src/...` |
| 6 | Bash | `for f in src/views/__init__.py src/views/serializers.py src/views/produto_routes.py src/views/usuario_routes.py src/views/pedido_routes.py src/view...` |
| 7 | Bash | `find . -name "*.py" -not -path "./.git/*" -not -path "./.claude/*" -not -path "*/__pycache__/*" \| sort \| xargs wc -l \| tail -5 && echo "--- total p...` |
| 8 | Bash | `sed -n '1,200p' <repo>/code-smells-project/.claude/skills/refactor-arch/references/report-template.md` |
| 9 | Bash | `cat <repo>/code-smells-project/.claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 10 | Bash | `echo "--- AP-01 secrets ---" && grep -rniE '(secret\|password\|passwd\|pwd\|api[_-]?key\|token\|private[_-]?key\|credential)\w*["\x27]?\s*[:=]\s*["\x27][^...` |
| 11 | Bash | `for pkg in "flask 3.1.3" "flask-cors 6.0.5" "werkzeug 3.1.8"; do set -- $pkg; echo "=== $1==$2 ==="; curl -s --max-time 25 "https://pypi.org/pypi/$...` |
| 12 | Bash | `echo "--- python ---" && python3 --version && echo "--- gitignore ---" && ls -a \| grep -i ignore; git check-ignore -v loja.db __pycache__ 2>&1 \| he...` |
| 13 | Bash | `echo "--- per-file LOC ---" && find . -name "*.py" -not -path "./.git/*" -not -path "./.claude/*" -not -path "*/__pycache__/*" \| sort \| xargs wc -l...` |
| 14 | Bash | `echo "toplevel: $(git rev-parse --show-toplevel)" && echo "--- ls .gitignore ---" && ls -la .gitignore 2>&1 && echo "--- check-ignore ---" && git c...` |
| 15 | Bash | `echo "--- ativo usage ---" && grep -rn "ativo" --include=*.py . ; echo "--- basicConfig / logger config ---" && grep -rn "basicConfig\\|getLogger" -...` |

</details>

<details>
<summary>Fase 3 — 37 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat <repo>/code-smells-project/.claude/skills/refactor-arch/references/validation-guide.md` |
| 2 | Bash | `sed -n '1,400p' <repo>/code-smells-project/.claude/skills/refactor-arch/references/mvc-guidelines.md` |
| 3 | Bash | `cd <repo>/code-smells-project/.claude/skills/refactor-arch/references && grep -n '^## T-\\|^# ' refactoring-playbook.md` |
| 4 | Bash | `cd <repo>/code-smells-project && VALIDATION_DIR="${TMPDIR:-/tmp}/refactor-arch/code-smells-project" && mkdir -p "$VALIDATION_DIR" && echo "VALIDATI...` |
| 5 | Bash | `uv venv .venv 2>&1 \| tail -3 && uv pip install --python .venv/bin/python -r requirements.txt 2>&1 \| tail -5 && .venv/bin/python -c "import flask, f...` |
| 6 | Bash | `cat > $TMP/refactor-arch/code-smells-project/smoke_test.py <<'PYEOF' """Smoke test do contrato da API da Loja. Uso: smoke_test.py <base_url> <saida...` |
| 7 | Bash | `V=$TMP/refactor-arch/code-smells-project && rm -f "$V/loja-baseline.db" && env DATABASE_PATH="$V/loja-baseline.db" PORT=5000 HOST=127.0.0.1 setsid ...` |
| 8 | Bash | `V=$TMP/refactor-arch/code-smells-project; for i in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:5000/" && break; sleep 0.5; done; echo "-...` |
| 9 | Bash | `V=$TMP/refactor-arch/code-smells-project && .venv/bin/python "$V/smoke_test.py" http://127.0.0.1:5000 "$V/baseline.json" 2>&1 \| tail -60` |
| 10 | Bash | `V=$TMP/refactor-arch/code-smells-project; python3 -c " import json d=json.load(open('$V/baseline.json')) for r in d: if r['check'] in ('405 metodo ...` |
| 11 | Bash | `V=$TMP/refactor-arch/code-smells-project && kill -- -"$(cat $V/../../refactor-arch/code-smells-project/server.pid 2>/dev/null \|\| cat $V/server.pid)...` |
| 12 | Bash | `V=$TMP/refactor-arch/code-smells-project && PID=$(cat "$V/server.pid" 2>/dev/null \|\| cat ./server.pid 2>/dev/null); echo "pid file: $PID"; ls -la "...` |
| 13 | Bash | `sleep 1; ss -ltn \| grep -w 5000 \|\| echo "port 5000 livre"; pgrep -af "app.py" \|\| echo "nenhum processo app.py"` |
| 14 | Bash | `cat > $TMP/refactor-arch/code-smells-project/admin_probe.py <<'PYEOF' """Probes dos endpoints /admin/* com token valido. Uso: admin_probe.py <base>...` |
| 15 | Bash | `rm -f $TMP/refactor-arch/code-smells-project/loja-admin-baseline.db && env DATABASE_PATH=$TMP/refactor-arch/code-smells-project/loja-admin-baseline...` |
| 16 | Bash | `pkill -f "\.venv/bin/python app.py"; sleep 1; ss -ltn \| grep -wE '5000\|5001' \|\| echo "portas 5000/5001 livres"` |
| 17 | Bash | `sleep 1; ss -ltn \| grep -wE '5000\|5001' \|\| echo "portas 5000/5001 livres"` |
| 18 | Bash | `cat > src/config/settings.py <<'PYEOF' """Configurações da aplicação lidas de variáveis de ambiente.""" import logging import os import secrets fro...` |
| 19 | Bash | `python3 - <<'PYEOF' import re, pathlib p = pathlib.Path("src/models/database.py") s = p.read_text() s = s.replace( '''"""Conexão SQLite por context...` |
| 20 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path("src/models/produto_model.py") s = p.read_text() s = s.replace( "from src.utils.errors import C...` |
| 21 | Bash | `perl -0pi -e 's/PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"\n\n\n\n/PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"\n\n\n/' src/models/prod...` |
| 22 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path("src/controllers/validators.py") s = p.read_text() s = s.replace( '''DADOS_INVALIDOS = "Dados i...` |
| 23 | Bash | `python3 - <<'PYEOF' import pathlib # controller de produto: reaproveita a constante do model em vez de repetir a mensagem p = pathlib.Path("src/con...` |
| 24 | Bash | `python3 - <<'PYEOF' import pathlib p = pathlib.Path("src/app.py") s = p.read_text() s = s.replace( "from src.config.settings import load_settings",...` |
| 25 | Bash | `cat > .env.example <<'EOF' # Variáveis de ambiente da API da Loja (valores fictícios). # Nada carrega este arquivo automaticamente: exporte as vari...` |
| 26 | Bash | `rm -f $TMP/refactor-arch/code-smells-project/loja-refactored.db && env DATABASE_PATH=$TMP/refactor-arch/code-smells-project/loja-refactored.db PORT...` |
| 27 | Bash | `.venv/bin/python $TMP/refactor-arch/code-smells-project/smoke_test.py http://127.0.0.1:5000 $TMP/refactor-arch/code-smells-project/refactored.json ...` |
| 28 | Bash | `cd $TMP/refactor-arch/code-smells-project && python3 - <<'PYEOF' import json b = json.load(open("baseline.json")) r = json.load(open("refactored.js...` |
| 29 | Bash | `echo "=== PROBE: hash/segredo em log ===" && grep -ciE 'scrypt\|pbkdf2\|SenhaForte123\|parameters' $TMP/refactor-arch/code-smells-project/server-refac...` |
| 30 | Bash | `rm -f $TMP/refactor-arch/code-smells-project/loja-admin-refactored.db && env DATABASE_PATH=$TMP/refactor-arch/code-smells-project/loja-admin-refact...` |
| 31 | Bash | `env DATABASE_PATH=$TMP/refactor-arch/code-smells-project/loja-race.db SEED_DATABASE=true .venv/bin/python - <<'PYEOF' """Prova que a existência do ...` |
| 32 | Bash | `env DATABASE_PATH=$TMP/refactor-arch/code-smells-project/loja-race.db .venv/bin/python - <<'PYEOF' """AP-11: existência verificada DENTRO da transa...` |
| 33 | Bash | `echo "=== segredos hardcoded ===" && grep -rnEi "(secret\|password\|passwd\|senha\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" --include...` |
| 34 | Bash | `echo "=== print() real (word boundary) ===" && grep -rnE "\bprint\(" --include=*.py src/ app.py \|\| echo " (nenhum — os hits anteriores eram 'bluepr...` |
| 35 | Bash | `pkill -f "\.venv/bin/python app.py"; sleep 1.5; ss -ltn \| grep -wE '5000\|5001' \|\| echo "portas 5000/5001 livres"; pgrep -af "app.py" \| grep -v pgre...` |
| 36 | Bash | `sleep 1; ss -ltn \| grep -wE '5000\|5001' \|\| echo "portas 5000/5001 livres"; echo; find . -name "__pycache__" -type d -not -path "./.venv/*" -exec rm...` |
| 37 | Bash | `echo "=== diffstat do projeto ===" && git diff --stat -- . && echo && echo "=== LOC final ===" && find . -name "*.py" -not -path "./.venv/*" -not -...` |

</details>
