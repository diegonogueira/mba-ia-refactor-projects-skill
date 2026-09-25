# Reexecução da skill (v1.6.1) — Projeto 2: `ecommerce-api-legacy` (Node.js/Express)

Execução final, que produziu o código versionado do projeto. Parte da saída de a v1.4.0 e usa a skill v1.6.1. Nessa versão, a autenticação das rotas de gestão de um finding AP-06 é correção obrigatória (`mvc-guidelines.md` §9, exceção 11), e isso inclui as ações feitas em nome de um usuário. Principal resultado: o checkout deixou de comprar em nome de uma conta existente sem a senha dela.

```bash
cd ecommerce-api-legacy
claude -p "/refactor-arch" --strict-mcp-config --output-format stream-json --verbose
claude -p "y" --resume f4b0d2be-7093-4867-8b4f-aa77266c7c84 --strict-mcp-config --output-format stream-json --verbose
```

| Etapa | Turnos | Duração | Custo (`total_cost_usd`) | Ferramentas |
|---|---|---|---|---|
| Fases 1 + 2 (somente leitura) | 12 | 2.2 min | US$ 0.84 | 11 |
| Fase 3 (após `y`) | 29 | 5.6 min | US$ 2.22 | 28 |

## Fase 1 — saída

```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js) [sem engines declarado; runtime local v26.8.1]
Framework:     Express 4.22.3 (^4.22.3 in package.json)
Dependencies:  sqlite3 6.0.1 (^6.0.1) — nativo; auth, validação, hash e log com node:crypto e módulos próprios
Domain:        LMS API com checkout (users, courses, enrollments, payments, audit_logs)
Architecture:  MVC em camadas — rotas só mapeiam URL→controller, services/models separados, config por env, composition root
Source files:  28 files analyzed (~747 lines of code)
Database:      SQLite via sqlite3 raw SQL com placeholders (:memory: por padrão, DATABASE_PATH)
DB tables:     users, courses, enrollments, payments, audit_logs
Entry point:   src/app.js → npm start (node src/app.js) (port 3000, host 127.0.0.1; schema + seed automáticos no boot)
Endpoints:     3 routes
  POST   /api/checkout               → checkoutController.checkout (src/views/routes.js:7 → src/controllers/checkoutController.js:6)
  GET    /api/admin/financial-report → adminGuard + reportController.financialReport (src/views/routes.js:8 → src/controllers/reportController.js:5)
  DELETE /api/users/:id              → adminGuard + userController.deleteUser (src/views/routes.js:9 → src/controllers/userController.js:7)
================================
```

## Fase 2 — saída

Relatório completo em [`reports/audit-project-2-rerun-v161.md`](../../reports/audit-project-2-rerun-v161.md). A mensagem terminou com:

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
src/
├── app.js                      # entry point: settings, banco, schema/seed, listen e encerramento limpo (SIGTERM/SIGINT → server.close → db.close)
├── createApp.js                # composition root: models, services, controllers, rotas e middlewares
├── config/settings.js          # settings lidos do ambiente, com padrões seguros
├── controllers/
│   ├── checkoutController.js
│   ├── reportController.js
│   └── userController.js
├── middlewares/
│   ├── adminGuard.js           # fechado por padrão (flag + token, timingSafeEqual)
│   ├── asyncHandler.js
│   └── errorHandler.js
├── models/
│   ├── database.js             # conexão SQLite, fila de operações e transações
│   ├── schema.js               # schema (users.email UNIQUE COLLATE NOCASE) e seed
│   ├── index.js                # createModels (sem o financialReport duplicado)
│   ├── userModel.js            # findCredentialsByEmail, create, deleteById
│   ├── courseModel.js
│   ├── enrollmentModel.js
│   ├── paymentModel.js
│   ├── auditLogModel.js
│   └── financialReportModel.js
├── services/
│   ├── checkoutService.js      # autentica a conta existente antes de cobrar e repete a checagem na transação
│   ├── paymentGateway.js
│   └── userService.js
├── utils/
│   ├── password.js             # hashPassword + verifyPassword (scrypt, custo lido do hash, timingSafeEqual)
│   ├── errors.js               # + UnauthorizedError (401)
│   ├── validators.js           # e-mail normalizado, cartão com 13–19 dígitos
│   ├── constants.js
│   └── logger.js
└── views/
    ├── routes.js
    └── presenters.js
```

### Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| Broken Authentication — checkout acts on an existing account without verifying the password | HIGH | Fixed | T-06 (+ T-04 verify) | `src/services/checkoutService.js`, `src/utils/password.js`, `src/models/userModel.js`, `src/utils/errors.js` |
| Missing Input Validation — e-mail not normalized, card number without length check | MEDIUM | Fixed | T-12 | `src/utils/validators.js`, `src/models/schema.js` |
| Deprecated Dependency — prebuild-install pulled by sqlite3 | MEDIUM | Not fixed | T-14 | — (ver Remaining Items) |
| Dead Code — unused model wiring and database close | LOW | Fixed | T-16 | `src/models/index.js`, `src/app.js` |

### Contract Changes

- **POST /api/checkout:** se o `eml` já tem conta e o `pwd` está ausente ou errado, a resposta agora é `401 Credenciais inválidas`, antes de qualquer cobrança (antes era 200 e a compra ficava na conta de outra pessoa). A checagem de senha vem antes da de matrícula duplicada. Com isso, a mensagem "já matriculado" não revela mais nada a quem não sabe a senha. Contas criadas sem `pwd` não autenticam em checkouts seguintes (401). Base: §9, exceção 11 (agir em nome de um usuário).
- **POST /api/checkout:** o `eml` é normalizado com `trim` e minúsculas, e o banco compara sem diferenciar maiúsculas. `VITIMA@Teste.com` agora cai na mesma conta que `vitima@teste.com` (antes criava uma segunda conta e cobrava de novo). Um e-mail com espaços nas pontas, que antes dava 400, agora é aceito depois de normalizado.
- **POST /api/checkout:** o `card` precisa ter de 13 a 19 dígitos, senão `400 Bad Request` (antes `"4"` era aprovado). O gateway passa a receber só os dígitos. Base: §9, exceção 6.
- Rotas, métodos, status de sucesso e corpos de resposta não mudaram.

### How to Run

```bash
npm install
npm start                      # http://127.0.0.1:3000, SQLite em memória com seed
## rotas administrativas (fechadas por padrão, respondem 403):
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN="$(openssl rand -hex 32)" npm start
## enviar o header X-Admin-Token nas rotas administrativas
```

### Validation

```text
  ✓ Application boots without errors (npm start, port 3000; Node v26.8.1)
  ✓ All endpoints respond correctly (16/16 checks match the baseline, covering all 3 routes; the report values are identical too)
  ✓ Wrong / missing password on an existing e-mail → 401, no charge logged (baseline: 200 and the enrollment attached to the victim)
  ✓ Guessed password on the seed account → 401 (baseline: 200)
  ✓ Account owner with the right password buys another course → 200; repeating the same wrong-password request → 401 again
  ✓ Concurrent race (same new e-mail, two requests, different passwords) → 200 / 401, and the loser's authorization is reversed ("Estornando autorização")
  ✓ E-mail case variant → 400 "Usuário já matriculado" (baseline: 200 and a second charge); after the probes the report shows "Vitima" only once in Docker
  ✓ Cards "4" and 20 digits → 400 (baseline: 200)
  ✓ Admin routes with no configuration → 403 (GET /api/admin/financial-report, DELETE /api/users/1)
  ✓ SIGTERM → "SIGTERM recebido, encerrando", exit code 0, port freed
  ✓ Re-audit: no hardcoded secrets, no interpolated SQL, no db calls in controllers/views, no deprecated APIs, npm audit 0 vulnerabilities
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-audit)
  ✗ Duplicate-key log probe not executed: the service checks the e-mail before inserting, and I could not force the UNIQUE error through the API
  ✗ 405/Allow and privilege-field probes not applicable: Express does not emit 405 here, and the API has no role/admin field
```

### Remaining Items

- **AP-18 — `prebuild-install@7.1.3` (deprecated, transitiva de `sqlite3@6.0.1`):** só é usada na instalação. O `sqlite3@6.0.1` já é a `latest` no registry e o §11 proíbe trocar o driver. Recomendação: atualizar o `sqlite3` quando sair uma versão que abandone o `prebuild-install`.
- **Diferença de forma em relação à minha recomendação do AP-14:** apliquei `COLLATE NOCASE` na coluna `users.email`, que vale para bancos novos (o padrão é `:memory:`). Um arquivo SQLite antigo, apontado por `DATABASE_PATH`, mantém a coluna antiga, porque `CREATE TABLE IF NOT EXISTS` não altera tabelas já existentes. Mesmo nesse caso, o validador grava tudo em minúsculas daqui em diante.

```text
================================
```

Os processos que iniciei foram encerrados e não sobrou nenhum artefato de execução no projeto (o banco é em memória; `node_modules/` está no `.gitignore`). Os resultados de baseline e de validação estão em `/tmp/refactor-arch/ecommerce-api-legacy/run-2026-09-25/`. Nada foi commitado. As mudanças estão em 10 arquivos do projeto, além das alterações nos arquivos da skill que já existiam antes.

## Linha do tempo das ferramentas

<details>
<summary>Fases 1 e 2 — 11 chamadas (nenhuma escrita)</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references && cat project-analysis.md report-template.md` |
| 2 | Bash | `cat anti-patterns-catalog.md` |
| 3 | Bash | `cd <repo>/ecommerce-api-legacy && cat package.json README.md .env.example api.http; git log --oneline -5 -- . ; wc -l src/*.js src/*/*.js` |
| 4 | Bash | `for f in src/app.js src/createApp.js src/config/settings.js src/controllers/*.js src/middlewares/*.js src/views/*.js; do echo "=== $f"; cat -n $f; don...` |
| 5 | Bash | `for f in src/models/*.js src/services/*.js src/utils/*.js; do echo "=== $f"; cat -n $f; done` |
| 6 | Bash | `cd <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references && grep -n "^## \\|^### " mvc-guidelines.md; awk '/^## 9/,0' mvc-guidelines.md` |
| 7 | Bash | `cd <repo>/ecommerce-api-legacy && git log --oneline --reverse -- src \| head -3; first=$(git log --reverse --format=%h -- src \| head -1); git show $fir...` |
| 8 | Bash | `npm audit --package-lock-only 2>&1 \| tail -20; grep -n '"deprecated"' package-lock.json \| head; node -e 'const l=require("./package-lock.json");for(co...` |
| 9 | Bash | `sed -n 940,960p package-lock.json; npm ls --package-lock-only --all 2>/dev/null \| grep -n -B3 "$(sed -n 945,950p package-lock.json \| grep -o '"node_mo...` |
| 10 | Bash | `npm ls --package-lock-only prebuild-install 2>&1; npm view sqlite3 version dist-tags --json 2>&1 \| head -8; grep -n "pass\b\\|\.pass\\|pass " -r src \| h...` |
| 11 | Bash | `for n in close rollbackError DENIED financialReport NotFoundError AppError exec debug createModels; do echo "$n: $(grep -rnw "$n" src \| wc -l)"; done;...` |

</details>

<details>
<summary>Fase 3 — 28 chamadas</summary>

| # | Ferramenta | Entrada (resumida) |
|---|---|---|
| 1 | Bash | `cd <repo>/ecommerce-api-legacy/.claude/skills/refactor-arch/references && cat validation-guide.md; grep -n "^## \\|^### " refactoring-playbook.md` |
| 2 | Bash | `sed -n 1,43p refactoring-playbook.md; sed -n 260,323p refactoring-playbook.md; sed -n 893,950p refactoring-playbook.md` |
| 3 | Bash | `cd <repo>/ecommerce-api-legacy && V=$TMP/refactor-arch/ecommerce-api-legacy && mkdir -p $V && npm ci 2>&1 \| tail -3 && node -e "require('sqlite3');con...` |
| 4 | Write | `$TMP/refactor-arch/ecommerce-api-legacy/smoke_test.py` |
| 5 | Write | `$TMP/refactor-arch/ecommerce-api-legacy/probes.py` |
| 6 | Bash | `ls -la $TMP/refactor-arch/ecommerce-api-legacy/; head -5 $TMP/refactor-arch/ecommerce-api-legacy/smoke_test.py` |
| 7 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && mkdir -p $V && mv $TMP/refactor-arch/ecommerce-api-legacy/probes.py $V/ && echo ok` |
| 8 | Write | `$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25/smoke_test.py` |
| 9 | Write | `$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25/run.sh` |
| 10 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && cd $V && python3 - <<'EOF' p=open('probes.py').read() p=p.replace('''import sys from smoke...` |
| 11 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && cd $V && python3 - <<'EOF' p=open('probes.py').read() p=p.replace('''show("case variant sa...` |
| 12 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && cd $V && ./run.sh probes-baseline probes.py > probes-baseline.txt 2>&1; wc -l probes-basel...` |
| 13 | Bash | `cat > src/utils/password.js <<'EOF' const crypto = require('crypto'); const { promisify } = require('util'); const scrypt = promisify(crypto.scrypt); ...` |
| 14 | Edit | `<repo>/ecommerce-api-legacy/src/utils/password.js` |
| 15 | Bash | `python3 - <<'EOF' p='src/utils/validators.js'; s=open(p).read() s=s.replace('''const POSITIVE_INTEGER_PATTERN = /^[1-9]\\d*$/; ''','''const CARD_SEPAR...` |
| 16 | Bash | `python3 - <<'EOF' p='src/models/schema.js'; s=open(p).read() s=s.replace(''' email TEXT NOT NULL UNIQUE,''',''' email TEXT NOT NULL UNIQUE COLLATE NOC...` |
| 17 | Bash | `python3 - <<'EOF' p='src/services/checkoutService.js'; s=open(p).read() old_imports='''const { hashPassword } = require('../utils/password'); const { ...` |
| 18 | Bash | `python3 - <<'EOF' p='src/app.js'; s=open(p).read() old=''' server.on('error', (err) => { logger.error('Falha no servidor HTTP', err); process.exit(1);...` |
| 19 | Bash | `python3 - <<'EOF' p='README.md'; s=open(p).read() old='''- Um usuário não pode se matricular duas vezes no mesmo curso''' assert old in s s=s.replace(...` |
| 20 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && cd $V && ./run.sh refactored smoke_test.py http://127.0.0.1:3000 refactored.json && python...` |
| 21 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 && cd <repo>/ecommerce-api-legacy && setsid npm start > $V/server-noconfig.log 2>&1 < /dev/nu...` |
| 22 | Bash | `cat $TMP/claude-1000/-home-diego-projects-mba-mba-ia-refactor-projects-skill-ecommerce-api-legacy/f4b0d2be-7093-4867-8b4f-aa77266c7c84/tasks/bq3q0wkua...` |
| 23 | Bash | `pkill -f "node src/app.js"; kill 2018834 2018836 2>/dev/null; sleep 1; pgrep -af "node src/app.js" \|\| echo "none running"; V=$TMP/refactor-arch/ecomme...` |
| 24 | Bash | `pgrep -af "node src/app.js" \|\| echo "none running"; grep -v "npm notice" $TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25/server-noconfig.log` |
| 25 | Bash | `V=$TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25 ( node src/app.js > $V/server-shutdown.log 2>&1; echo "exit code: $?" >> $V/server-shutdown.l...` |
| 26 | Bash | `sleep 1; pgrep -af "src/app.js" \| grep -v pgrep; cat $TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25/server-shutdown.log \| tail -2` |
| 27 | Bash | `kill -TERM 2021476; sleep 1.5; tail -2 $TMP/refactor-arch/ecommerce-api-legacy/run-2026-09-25/server-shutdown.log; ss -ltn \| grep :3000 \|\| echo "port ...` |
| 28 | Bash | `echo "secrets:"; grep -rnEi "(secret\|password\|passwd\|api[_-]?key\|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" src; echo "sql interp:"; grep -rnE "(r...` |

</details>
