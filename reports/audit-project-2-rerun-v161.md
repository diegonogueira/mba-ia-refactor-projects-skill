# Audit Report — ecommerce-api-legacy (reauditoria final, skill v1.6.1)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.6.1), gerada por `claude -p "/refactor-arch"` dentro de `ecommerce-api-legacy/`
> (modelo `claude-opus-5-5`, Claude Code 2.1.282, sessão `f4b0d2be-7093-4867-8b4f-aa77266c7c84`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 0 · HIGH 1 · MEDIUM 2 · LOW 1 · Total 4.
> Esta execução produziu o código versionado do projeto. Ela audita o código já refatorado, por isso sobram poucos findings; o relatório do código legado é o [`audit-project-2.md`](audit-project-2.md).

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.3
Files:   28 analyzed | ~747 lines of code
```

## Summary

CRITICAL: 0 | HIGH: 1 | MEDIUM: 2 | LOW: 1

## Findings

### [HIGH] Broken Authentication — checkout acts on an existing account without verifying the password
- **ID:** AP-06
- **File:** `src/services/checkoutService.js:35-36`, `src/services/checkoutService.js:51-54`, `src/utils/validators.js:21`, `src/utils/validators.js:31`, `src/utils/password.js:13-17`, `src/models/userModel.js:9-14`
- **Description:** Quando o `eml` enviado já existe, `checkout()` usa a conta encontrada por `users.findByEmail(email)` (`const userId = user ? user.id : ...`) e ignora `pwd`. Em nenhum ponto a senha é conferida: `utils/password.js` só exporta `hashPassword`, não há função de verificação, e `pwd` é opcional (`validPassword = password === undefined || ...`). Assim, contas novas podem ser criadas sem credencial (`passwordHash = null`, que grava `pass` NULL).
- **Impact:** Um cliente anônimo que sabe o e-mail de outra pessoa cria matrículas e pagamentos em nome dela (IDOR). Com isso, o relatório financeiro e o `audit_logs` passam a atribuir compras a quem não as fez, e a própria vítima recebe `400 Usuário já matriculado` quando tenta comprar o curso. A senha enviada no checkout funciona só na escrita e não protege nada.
- **Recommendation:** Criar `verifyPassword(password, stored)` em `utils/password.js`, lendo os parâmetros de custo gravados no hash e comparando com `crypto.timingSafeEqual`. No `checkout()`, quando o e-mail já existe, exigir `pwd` e verificá-lo **antes** de autorizar o cartão; senha ausente, errada ou conta sem credencial (`pass` NULL) → `401` com o corpo em texto do projeto, sem cobrança. Repetir a verificação dentro da transação para quem entra pela primeira vez na corrida. O modelo expõe `findCredentialsByEmail` separado de `findByEmail`, para que o hash nunca apareça em outras leituras. A rota continua pública, porque o cliente se identifica pelas credenciais da própria requisição. (Playbook T-06)

### [MEDIUM] Missing Input Validation — e-mail not normalized, card number without length check
- **ID:** AP-14
- **File:** `src/utils/validators.js:3-4`, `src/utils/validators.js:18`, `src/utils/validators.js:24-25`, `src/utils/validators.js:31`, `src/models/schema.js:12`, `src/models/userModel.js:3-4`
- **Description:** `validateCheckoutInput` devolve `eml` e `usr` como vieram, sem `trim()` nem minúsculas. A coluna `email TEXT NOT NULL UNIQUE` e o `WHERE email = ?` diferenciam maiúsculas de minúsculas. `CARD_NUMBER_PATTERN` (`/^\d+(?:[ -]?\d+)*$/`) aceita qualquer quantidade de dígitos, então `"card": "4"` é aprovado pelo gateway simulado.
- **Impact:** `Gui@x.com` e `gui@x.com` viram duas contas. Isso burla a regra "um usuário não se matricula duas vezes no mesmo curso" e gera uma cobrança duplicada da mesma pessoa. Números de cartão impossíveis chegam ao gateway e ficam registrados como `PAID`.
- **Recommendation:** Normalizar no validador (`email.trim().toLowerCase()`, `name.trim()`) e declarar `email ... UNIQUE COLLATE NOCASE` no schema, para que a unicidade valha também no banco. Validar o cartão com 13–19 dígitos depois de remover espaços e hífens, respondendo `400 Bad Request` como os demais erros de validação. (Playbook T-12)

### [MEDIUM] Deprecated Dependency — prebuild-install pulled by sqlite3
- **ID:** AP-18
- **File:** `package-lock.json:948-952`
- **Description:** `npm audit --package-lock-only` retornou `found 0 vulnerabilities`. Mas o lockfile marca `prebuild-install@7.1.3` como `"deprecated": "No longer maintained..."`, e `npm ls` mostra que ele vem de `sqlite3@6.0.1`. É o que o próprio `sqlite3` usa na instalação para baixar o binário nativo. `sqlite3@6.0.1` já é a `latest` no registry. No código, nenhuma API obsoleta do Express 4.22.3/Node foi encontrada (`req.param(`, `res.send(status)`, `new Buffer(`, `url.parse(`, `body-parser`: 0 ocorrências).
- **Impact:** Só afeta a instalação, não o runtime. Mesmo assim, a cadeia de build do driver nativo depende de um pacote sem manutenção, que não vai receber correções se aparecer uma vulnerabilidade.
- **Recommendation:** Não existe versão do `sqlite3` sem essa dependência, e o guia proíbe trocar o driver. Manter a versão, registrar o item em "Remaining Items" e acompanhar a próxima release do `sqlite3`. Sem mudança de código. (Playbook T-14)

### [LOW] Dead Code — unused model wiring and database close
- **ID:** AP-22
- **File:** `src/models/index.js:6`, `src/models/index.js:16`, `src/models/database.js:58-60`
- **Description:** `createModels()` monta `financialReport: createFinancialReportModel(db)`, mas ninguém lê `models.financialReport`. O `createApp.js:2,22` importa e instancia o model direto, o que cria dois caminhos de montagem para o mesmo model. `close()` do handle do banco nunca é chamado: não há tratamento de `SIGTERM`/`SIGINT` em `src/app.js`.
- **Impact:** Montagem duplicada e confusa, e uma API do banco sem uso. Quem lê o código fica sem saber qual caminho de composição vale.
- **Recommendation:** Tirar `financialReport` de `createModels` e manter a montagem só no composition root. Ligar `db.close()` a um encerramento limpo (`server.close()` seguido de `db.close()` em `SIGTERM`/`SIGINT`) em `src/app.js`, ou remover o método. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `package-lock.json:948-952` | `prebuild-install@7.1.3` (transitiva de `sqlite3@6.0.1`), marcada "No longer maintained" | Nenhuma disponível no `sqlite3` atual (6.0.1 é a `latest`); atualizar quando o `sqlite3` abandonar essa dependência |

```text
================================
Total: 4 findings
================================
```

Este projeto já foi refatorado para MVC numa execução anterior, então a auditoria achou poucos problemas. As duas rotas administrativas (`/api/admin/...` e exclusão de conta) já estão fechadas por padrão com flag + token, como exige a exceção 2, e por isso não geraram finding. Há alterações não commitadas nos arquivos da skill; recomendo fazer commit ou backup antes da Fase 3.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
