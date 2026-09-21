# Reexecução da skill (v1.4.0) — Projeto 2: `ecommerce-api-legacy` (Node.js/Express)

Execução com a skill v1.4.0, que fecha o padrão sistêmico identificado na varredura finding-a-finding (guard fechado por padrão, headers do framework no contrato, sem segredo em log/seed).

Diferente das execuções de `docs/execution-logs/project-2-*.md`, aqui a Fase 1 analisa o **código já refatorado** — por isso a arquitetura detectada é "MVC em camadas" e os achados são o que sobrou.

```bash
cd ecommerce-api-legacy
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume b48fad9d-89ac-4119-8da0-8f1719fc445e --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 17 | 6.1 min | US$ 1.60 | 16 |
| Fase 3 (após `y`) | 28 | 12.8 min | US$ 5.71 | 27 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js) [sem campo `engines`; runtime local: Node v26.8.1]
Framework:     Express 4.22.3 (`^4.22.3` em package.json:10 → 4.22.3 resolvido no package-lock.json)
Dependencies:  sqlite3 6.0.1 (driver nativo, SQL puro); nenhuma outra dependência de runtime
Domain:        LMS com fluxo de checkout de cursos (users, courses, enrollments, payments, audit_logs)
Architecture:  MVC em camadas — rotas só ligam URL→controller, controllers finos, SQL só nos models, config e erros centralizados
Source files:  28 files analyzed (~666 lines of code)
Database:      SQLite via sqlite3 (SQL puro com placeholders `?`, conexão única em src/models/database.js:64-71) — `:memory:` por padrão
DB tables:     users, courses, enrollments, payments, audit_logs (src/models/schema.js:5-36)
Entry point:   src/app.js → `npm install && npm start` (port 3000, host 127.0.0.1)
Endpoints:     3 routes
  POST   /api/checkout                 → checkoutController.checkout   (src/controllers/checkoutController.js:6; rota em src/views/routes.js:7)
  GET    /api/admin/financial-report   → reportController.financialReport (src/controllers/reportController.js:5; rota em src/views/routes.js:8)
  DELETE /api/users/:id                → userController.deleteUser     (src/controllers/userController.js:5; rota em src/views/routes.js:9)
================================
```

Observações de suporte: o composition root é `src/createApp.js:13-31` (models → services → controllers → rotas → middlewares), a configuração vem do ambiente em `src/config/settings.js:16-24`, schema/seed rodam no boot (`src/app.js:12-13`) e o banco em memória é recriado a cada inicialização.

---

## Fase 2 — saída

Relatório completo em [`reports/audit-project-2-rerun.md`](../../reports/audit-project-2-rerun.md). A mensagem terminou com:

```text
O ponto central: o projeto **já está em MVC em camadas** (dependências apontando para baixo, SQL só nos models, erro centralizado, injeção via composition root), então não há achados de AP-01/02/03/07/08/09/10 — o que sobra é segurança de configuração (a guarda administrativa aberta por padrão, que é CRITICAL), uma regra de negócio ausente no checkout e ajustes de robustez/limpeza.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Resposta enviada: `y`

## Fase 3 — saída

> Títulos rebaixados um nível para caber neste documento; conteúdo sem alterações.

Refactor complete and validated. Final report:

```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

O projeto já estava em MVC em camadas, então a estratégia foi a da linha "Already MVC" do §10 das guidelines: **nenhum arquivo criado, movido ou removido** — 15 arquivos alterados no lugar para fechar os achados. Runtime usado nas duas rodadas: Node v26.8.1 / npm 12.0.2.

### New Project Structure

```text
ecommerce-api-legacy/
├── package.json                      # npm start → node src/app.js (inalterado)
├── .env.example                      # (M) + ADMIN_ENDPOINTS_ENABLED, SEED_USER_PASSWORD
├── README.md                         # (M) rotas admin fechadas por padrão + regras de negócio
├── api.http                          # (M) exemplos com X-Admin-Token e caso de duplicata
└── src/
    ├── app.js                        # (M) entry point: seed recebe a senha do ambiente; aviso de rotas fechadas
    ├── createApp.js                  # (M) composition root: instancia só o model injetado; passa a flag da guarda
    ├── config/
    │   └── settings.js               # (M) + adminEndpointsEnabled, seedUserPassword (parse booleano)
    ├── models/
    │   ├── database.js               #     conexão SQLite única, fila serializada e transações
    │   ├── schema.js                 # (M) UNIQUE (user_id, course_id); seed sem senha conhecida
    │   ├── index.js                  #     factory dos models por escopo (handle ou transação)
    │   ├── userModel.js              # (M) create() recebe passwordHash, nunca a senha crua
    │   ├── enrollmentModel.js        # (M) + findByUserAndCourse()
    │   ├── courseModel.js            #     busca de curso ativo
    │   ├── paymentModel.js           #     pagamentos por matrícula
    │   ├── auditLogModel.js          #     trilha de auditoria
    │   └── financialReportModel.js   #     relatório em uma query + agregação
    ├── services/
    │   ├── checkoutService.js        # (M) duplicata, KDF fora da transação e estorno compensatório
    │   ├── paymentGateway.js         # (M) authorize() devolve authorizationId; + voidAuthorization()
    │   └── userService.js            #     exclusão em cascata transacional
    ├── controllers/
    │   ├── checkoutController.js     #     valida → service → presenter
    │   ├── reportController.js       #     model → presenter
    │   └── userController.js         # (M) valida o :id e traduz "nada apagado" em 404
    ├── views/
    │   ├── routes.js                 #     URL + método → controller (inalterado)
    │   └── presenters.js             #     serializadores das respostas
    ├── middlewares/
    │   ├── adminGuard.js             # (M) fechada por padrão (403), abre com flag + token
    │   ├── errorHandler.js           #     handler central + 404 handler
    │   └── asyncHandler.js           #     propaga rejeições para o handler central
    └── utils/
        ├── validators.js             # (M) + validateUserId()
        ├── password.js               # (M) scrypt N=2^17 com custo gravado no hash
        ├── errors.js, constants.js, logger.js
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| AP-06 Unprotected Destructive/Admin Endpoints — guarda opt-in | CRITICAL | Fixed | T-06 | `src/middlewares/adminGuard.js:13-20`, `src/config/settings.js:25-26`, `src/app.js:15-17` |
| AP-14 Missing Business-Rule Validation — checkout duplicado | HIGH | Fixed | T-12, T-09 | `src/services/checkoutService.js:11-15,38-40,55-57`, `src/models/enrollmentModel.js:3-8`, `src/models/schema.js:34-36` |
| AP-14 Inconsistent Response — delete de usuário inexistente | MEDIUM | Fixed | T-12, T-07 | `src/controllers/userController.js:8-10`, `src/utils/validators.js:35-39` |
| AP-13 Performance — hash scrypt dentro da transação | MEDIUM | Fixed | T-09, T-08 | `src/services/checkoutService.js:43`, `src/models/userModel.js:8-15` |
| AP-11 Non-atomic Operation — pagamento sem compensação | MEDIUM | Partially fixed | T-09 | `src/services/checkoutService.js:20-28,62-65`, `src/services/paymentGateway.js:13-24` |
| AP-18 Deprecated Dependency — `prebuild-install` | LOW | Not fixed | T-14 | — (sem correção upstream; ver Remaining Items) |
| AP-19 Inconsistent Response Envelopes — JSON vs texto puro | LOW | Not fixed | T-07 | — (bloqueado por contrato; ver Remaining Items) |
| AP-22 Dead Code — 5 models instanciados sem uso | LOW | Fixed | T-16 | `src/createApp.js:2,15-24` |
| AP-05 Weak Password Policy — sem tamanho mínimo e seed `123` | LOW | Partially fixed | T-04, T-12 | `src/utils/password.js:8-20`, `src/models/schema.js:44-49`, `src/config/settings.js:28` |

### Contract Changes

- **CC1 — `GET /api/admin/financial-report` e `DELETE /api/users/:id`:** fechadas por padrão. Sem `ADMIN_ENDPOINTS_ENABLED=true` **e** `ADMIN_TOKEN`, respondem `403 "Rotas administrativas desabilitadas"` onde antes respondiam `200`. Com as duas variáveis e o token correto o comportamento é **idêntico ao original** (verificado na rodada B); token errado/ausente segue `403 "Acesso negado"`. Exceção 2 de `mvc-guidelines.md` §9.
- **CC2 — `POST /api/checkout`:** o segundo checkout do mesmo `eml` no mesmo `c_id` responde `400 "Usuário já matriculado neste curso"` e **não cobra o cartão** (antes: `200` com matrícula e pagamento duplicados). Exceção 6 (§9). Efeito colateral visível: o `enrollment_id` da requisição seguinte é menor, porque a linha duplicada não é mais criada.
- **CC3 — `DELETE /api/users/:id` com id não inteiro:** `400 "Bad Request"` (antes: `200` com mensagem de sucesso sem ter apagado nada).
- **CC4 — `DELETE /api/users/:id` de usuário inexistente ou já removido:** `404 "Usuário não encontrado"` (antes: `200` com mensagem de sucesso falsa).
- **Interno, sem efeito na API:** senha do seed vem de `SEED_USER_PASSWORD` (ou é aleatória) em vez de `123`; o hash passou a gravar o custo (`scrypt$131072$8$1$<salt>$<key>`).
- **Preservado:** rotas, métodos, nomes de campos (`usr`, `eml`, `pwd`, `c_id`, `card`), status e corpos de sucesso, erros em texto puro, header `Allow: POST` no `OPTIONS`, `404 "Not Found"` em rota/método inexistente, porta `3000` e `npm start`.

CC3 e CC4 são as duas mudanças que minha própria recomendação da Fase 2 marcou como "precisa de confirmação": implementei porque corrigem uma resposta falsa, mas são reversíveis em duas linhas de `src/controllers/userController.js` se você preferir manter o `200`.

### How to Run

```bash
npm install
npm start                                  # rotas admin fechadas (403)

# com as rotas administrativas habilitadas:
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN="$(openssl rand -hex 32)" npm start
curl -H "X-Admin-Token: $ADMIN_TOKEN" http://127.0.0.1:3000/api/admin/financial-report
```

### Validation

```text
  ✓ Application boots without errors (npm start, port 3000) — 4 boots (2 baseline + 2 refatorado), 0 linhas de erro nos logs
  ✓ All endpoints respond correctly (46/46 checks conciliados: 26 idênticos + 20 mudanças de contrato documentadas, 0 regressões)
  ✓ Cobertura do inventário da Fase 1: 3/3 rotas exercitadas (23 checks por configuração, em 2 configurações)
  ✓ Endpoint destrutivo/admin sem configuração responde 403, não 200 (8 checks da rodada A)
  ✓ Rotas admin com flag + token válido voltam a 200; token errado ou ausente = 403 (rodada B, idêntico ao baseline)
  ✓ Matrícula duplicada rejeitada com 400 e receita não mais duplicada (Docker 994 vs 1491 no baseline)
  ✓ Campos de privilégio de cliente anônimo ({"role":"admin","is_admin":true,"pass":...}) ignorados; domínio sem coluna de privilégio (users: id, name, email, pass)
  ✓ Erro forçado em escrita (banco somente-leitura): cliente recebe 500 genérico e o log não traz parâmetros vinculados (senhaforte/scrypt$/e-mail/"parameters" = 0 ocorrências)
  ✓ Autorização estornada quando a gravação falha; falha no estorno é logada sem mascarar o erro original
  ✓ Header decorado pelo framework preservado (Allow: POST no OPTIONS /api/checkout, igual ao baseline)
  ✓ Credencial gravada como scrypt$131072$8$1$<salt>$<key>; campo `pass` enviado pelo cliente não é armazenado
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-auditoria: sem SQL concatenado, sem acesso a dados em controllers/views, guarda fechada por padrão, sem imports mortos, npm audit = 0 vulnerabilities)
```

### Remaining Items

- **AP-11 (Partially fixed):** o estorno funciona, mas **não há registro da intenção de pagamento antes da autorização** — minha recomendação pedia as duas coisas. Se o processo morrer entre `authorize()` e o `catch`, a autorização não deixa rastro local. Fechar isso exige uma coluna `authorization_id` e um status `PENDING` em `payments` (mudança de schema com migração), fora do que cabe num refactor sem migração.
- **AP-05 (Partially fixed):** custo do scrypt e senha de seed corrigidos; **tamanho mínimo de senha (≥ 8) e recusa explícita de `pwd: ""` não entraram** — transformariam requisições hoje aceitas (`200`) em `400`, o que §9 lista como não permitido sem sua autorização. Recomendo ativar junto com a criação do endpoint de login.
- **AP-19 (Not fixed):** padronizar tudo em um envelope JSON muda o envelope de resposta — proibido por §9 sem sua autorização. Recomendação mantida para uma v2 da API.
- **AP-18 (Not fixed):** `prebuild-install@7.1.3` continua depreciado como dependência transitiva de `sqlite3@6.0.1`; só é usado no build do binário nativo, `npm audit` segue em 0 vulnerabilidades e não existe versão corrigida a montante. Acompanhar releases do `sqlite3`.
- **Autenticação de verdade:** `POST /api/checkout` continua público (como no original) e as rotas admin usam um único token estático, sem identidade, rotação ou trilha de quem chamou. Tornar rotas públicas autenticadas é exatamente o caso que §9 manda deixar aqui como recomendação.

```text
================================
```

Dois pontos fora do relatório que você deve saber:

1. **Mudanças concorrentes no repositório.** O `git status` do repositório-pai mostra `code-smells-project/` modificado (mtimes 12:10–12:11, durante esta sessão). Não toquei nesse diretório — provavelmente há outra sessão rodando a skill nas outras cópias em paralelo. Meu diff está confinado a `ecommerce-api-legacy/` (15 arquivos).
2. **Nada foi commitado** e nenhum artefato ficou dentro do projeto (sem `*.db`, sem logs; `node_modules/` segue ignorado). Os artefatos de validação — smoke test, baselines, comparador e logs dos servidores — estão em `/tmp/refactor-arch/ecommerce-api-legacy/`, caso você queira reexecutar: `run.sh <tag>` sobe, testa e derruba o servidor, e `compare.py` refaz a conciliação com o baseline.

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 16 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references/project-analysis.md` |
| 2 | Bash | `echo "=== package.json ===" && cat package.json && echo "=== README.md ===" && cat README.md && echo "=== .env.example ===" && cat .env.example && ...` |
| 3 | Bash | `for f in src/app.js src/createApp.js src/config/settings.js src/views/routes.js src/views/presenters.js; do echo "=============== $f"; cat -n "$f";...` |
| 4 | Bash | `for f in src/controllers/*.js src/middlewares/*.js; do echo "=============== $f"; cat -n "$f"; done` |
| 5 | Bash | `for f in src/models/*.js; do echo "=============== $f"; cat -n "$f"; done` |
| 6 | Bash | `for f in src/services/*.js src/utils/*.js; do echo "=============== $f"; cat -n "$f"; done; echo "=============== api.http"; cat -n api.http` |
| 7 | Bash | `cat <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references/anti-patterns-catalog.md` |
| 8 | Bash | `cat <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references/report-template.md` |
| 9 | Bash | `echo "=== lockfile versions ===" && node -e "const l=require('./package-lock.json'); for(const [k,v] of Object.entries(l.packages\|\|{})) if(k) conso...` |
| 10 | Bash | `echo "=== AP-02 injection (template/concat in SQL) ==="; grep -rnE '(run\|get\|all\|query\|exec)\(\s*\|\+\s*(email\|id\|name\|userId\|courseId)' --include=...` |
| 11 | Bash | `sed -n 940,960p package-lock.json && echo "=== who depends on it ===" && node -e " const l=require('./package-lock.json'); const dep=Object.entries...` |
| 12 | Bash | `echo "=== node/npm ==="; node -v; npm -v; echo "=== node_modules present? ==="; ls -d node_modules 2>/dev/null \|\| echo "absent"; echo "=== gitignor...` |
| 13 | Bash | `echo "=== usage of models.* ==="; grep -rn 'models\.' --include=*.js src/; echo; echo "=== AppError / ValidationError / errors usage ==="; for n in...` |
| 14 | Bash | `sed -n '1,400p' .claude/skills/refactor-arch/references/mvc-guidelines.md \| grep -n -A 60 -i "contract preservation"` |
| 15 | Bash | `echo "--- adminGuard"; grep -n 'adminToken\\|next()' src/middlewares/adminGuard.js; echo "--- settings"; grep -n 'adminToken' src/config/settings.js...` |
| 16 | Bash | `cd /tmp && node -e " const crypto=require('crypto');const {promisify}=require('util');const scrypt=promisify(crypto.scrypt); (async()=>{const t=Dat...` |

</details>

<details>
<summary>Fase 3 — 27 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cat <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references/validation-guide.md` |
| 2 | Bash | `sed -n '1,120p' .claude/skills/refactor-arch/references/refactoring-playbook.md` |
| 3 | Bash | `awk '/^## T-06/,/^## T-08/' .claude/skills/refactor-arch/references/refactoring-playbook.md` |
| 4 | Bash | `awk '/^## T-09/,/^## T-11/' .claude/skills/refactor-arch/references/refactoring-playbook.md; awk '/^## T-12/,/^## T-13/' .claude/skills/refactor-ar...` |
| 5 | Bash | `VD="${TMPDIR:-/tmp}/refactor-arch/ecommerce-api-legacy" && mkdir -p "$VD" && echo "VALIDATION_DIR=$VD" && node -v > "$VD/runtime.txt" && npm -v >> ...` |
| 6 | Bash | `cat > $TMP/refactor-arch/ecommerce-api-legacy/smoke_test.py <<'PY' import json, os, sys, urllib.request, urllib.error BASE = sys.argv[1] OUT = sys....` |
| 7 | Bash | `cd $TMP/refactor-arch/ecommerce-api-legacy && sed -i 's\|("delete-user-anonymous", "DELETE", "/api/users/2"\|("delete-user-anonymous", "DELETE", "/ap...` |
| 8 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy run_smoke() { # $1=tag $2=env-prefix-desc ; env vars come from the caller setsid npm start > "$VD/server...` |
| 9 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy && echo "=== log B (falha esperada) ==="; cat "$VD/server-baseline-b.log" \| tail -8 echo "=== matando qu...` |
| 10 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy; echo "=== porta 3000 ==="; ss -ltnp 2>/dev/null \| grep ':3000' \|\| echo "livre"; echo "=== run.sh existe...` |
| 11 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy cat > "$VD/run.sh" <<'SH' #!/usr/bin/env bash # run.sh <tag> — boots the app in its own session/process ...` |
| 12 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy echo "################ BASELINE RUN A (sem configuração) ################" ( env -u ADMIN_TOKEN -u ADMIN...` |
| 13 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy; python3 - <<'PY' import json for tag in ('baseline-a','baseline-b'): d=json.load(open(f'$TMP/refactor-a...` |
| 14 | Bash | `cd /tmp && node -e " const crypto=require('crypto');const {promisify}=require('util');const scrypt=promisify(crypto.scrypt); (async()=>{ for (const...` |
| 15 | Bash | `cd <repo>/ecommerce-api-legacy # ---------- 1. config ---------- cat > src/config/settings.js <<'JS' const DEFAULT_PORT = 3000; const DEFAULT_HOST ...` |
| 16 | Bash | `cd <repo>/ecommerce-api-legacy cat > src/models/schema.js <<'JS' const crypto = require('crypto'); const { hashPassword } = require('../utils/passw...` |
| 17 | Bash | `cd <repo>/ecommerce-api-legacy # ---------- 4. controllers + validators ---------- cat > src/utils/validators.js <<'JS' const { ValidationError } =...` |
| 18 | Bash | `cd <repo>/ecommerce-api-legacy cat > .env.example <<'ENV' # Variáveis de ambiente da LMS API. # Nada carrega este arquivo automaticamente: exporte ...` |
| 19 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy echo "################ REFACTORED RUN A (sem configuração) ################" ( env -u ADMIN_TOKEN -u ADM...` |
| 20 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy; cat > "$VD/compare.py" <<'PY' import json VD = "$TMP/refactor-arch/ecommerce-api-legacy" # (run, label)...` |
| 21 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy python3 - <<'PY' import json d={r['label']:r for r in json.load(open('$TMP/refactor-arch/ecommerce-api-l...` |
| 22 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy echo "=== PROBE 1: campo de privilégio enviado por cliente anônimo ===" echo "-- grep por campos de priv...` |
| 23 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy rm -f "$VD/probe.db" echo "=== passo 1: boot com DATABASE_PATH em arquivo + um checkout ===" setsid bash...` |
| 24 | Bash | `cd <repo>/ecommerce-api-legacy echo "=== AP-01 segredos/credenciais literais ==="; grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\...` |
| 25 | Bash | `VD=$TMP/refactor-arch/ecommerce-api-legacy echo "=== processos/porta ==="; ss -ltnp 2>/dev/null \| grep ':3000' \|\| echo "porta 3000 livre"; pgrep -a...` |
| 26 | Bash | `cd <repo> && echo "=== mtimes: code-smells-project (não toquei) ===" && ls -l --time-style=+%Y-%m-%d_%H:%M code-smells-project/src/models/database....` |
| 27 | Bash | `git diff --stat -- . \| tail -3 && echo "=== arquivos alterados (só neste projeto) ===" && git diff --name-only -- . && echo "=== estrutura ===" && ...` |

</details>
