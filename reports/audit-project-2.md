# Audit Report — ecommerce-api-legacy

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.1.0), gerada por `claude -p "/refactor-arch"` executado dentro de `ecommerce-api-legacy/`
> (modelo `claude-opus-5[1m]`, sessão `d9de1d3f-ef7f-450a-afa7-a3e97766874e`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 5 · HIGH 8 · MEDIUM 4 · LOW 4 · Total 21.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.1
Files:   3 analyzed | ~180 lines of code
```

## Summary

CRITICAL: 5 | HIGH: 8 | MEDIUM: 4 | LOW: 4

## Findings

### [CRITICAL] God Class / God Module
- **ID:** AP-03
- **File:** `src/AppManager.js:4-139`, `src/utils.js:1-25`
- **Description:** A classe `AppManager` faz tudo sozinha. Ela abre a conexão (`new sqlite3.Database(':memory:')`), cria o schema e o seed em `initDb()` e registra as três rotas em `setupRoutes(app)`. Também roda todo o SQL e aplica as regras de negócio: aprovação do pagamento, matrícula, auditoria e soma da receita. Já `utils.js` junta configuração, cache global e hash de senha.
- **Impact:** Não dá para testar nem mudar uma camada sem mexer nas outras. Para alterar uma regra de negócio é preciso editar o mesmo arquivo que tem as rotas, o SQL e o schema.
- **Recommendation:** Separar em `config/`, `models/` (conexão, schema/seed e uma entidade por módulo), `services/` (checkout e relatório), `controllers/`, `views/` (rotas) e um composition root. (Playbook T-03)

### [CRITICAL] Insecure Password Storage
- **ID:** AP-05
- **File:** `src/AppManager.js:18`, `src/AppManager.js:68`, `src/utils.js:17-23`
- **Description:** `badCrypto(pwd)` repete 10000 vezes os 2 primeiros caracteres de `Buffer.from(pwd).toString('base64')` e corta o resultado em 10. Na prática, o "hash" é só esse prefixo repetido: `"senhaforte"` vira `"c2c2c2c2c2"`. Não tem salt, revela o começo da senha e toda senha que começa com "sa"…"so" dá o mesmo valor. Quando `pwd` não é enviado, o checkout usa a senha padrão `p || "123456"`. O seed grava `'123'` em texto puro.
- **Impact:** Se a tabela `users` vazar, as senhas ficam triviais de descobrir ou forjar. Contas criadas sem senha ficam com uma senha conhecida. O loop de 10000 iterações ainda trava o event loop sem motivo.
- **Recommendation:** Usar `crypto.scrypt` com salt aleatório e aplicar o novo hash também ao seed. Quando `pwd` faltar, gerar uma senha aleatória em vez de `"123456"`, o que mantém o contrato. (Playbook T-04)

### [CRITICAL] Sensitive Data Exposure (responses and logs)
- **ID:** AP-04
- **File:** `src/AppManager.js:45`
- **Description:** A cada checkout, `console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)` grava no stdout o número completo do cartão (campo `card`) e a chave `pk_live_...` do gateway.
- **Impact:** O número do cartão e o segredo de pagamento vão parar em logs e agregadores. Isso viola o PCI-DSS e deixa os dados à vista de quem lê os logs.
- **Recommendation:** Nunca logar segredos, mascarar o cartão (`****4444`) e usar um logger com níveis. (Playbook T-05)

### [CRITICAL] Unprotected Destructive/Debug Endpoints and Broken Authentication — admin report and user deletion
- **ID:** AP-06
- **File:** `src/AppManager.js:80-129`, `src/AppManager.js:131-137`
- **Description:** Nenhuma das duas rotas tem autenticação ou autorização. `GET /api/admin/financial-report` devolve a receita por curso e o nome de cada aluno com o valor pago. `DELETE /api/users/:id` roda `DELETE FROM users WHERE id = ?`.
- **Impact:** Qualquer cliente anônimo consegue ler dados financeiros e pessoais. Também consegue apagar todos os usuários, bastando percorrer os `id`.
- **Recommendation:** Criar um middleware de token de admin (comparado com `crypto.timingSafeEqual`) e aplicá-lo nessas rotas. Isso muda o contrato de rotas hoje públicas, então precisa de decisão do usuário. (Playbook T-06)

### [CRITICAL] Hardcoded Credentials and Secrets
- **ID:** AP-01
- **File:** `src/utils.js:2-5`
- **Description:** O objeto `config` tem credenciais escritas direto no código: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` (prefixo de chave de produção) e `smtpUser: "no-reply@fullcycle.com.br"`. A chave do gateway ainda aparece no log (ver AP-04).
- **Impact:** Quem tem acesso ao repositório pega a senha do banco e a chave de produção do gateway. O segredo fica no histórico do git mesmo depois de removido.
- **Recommendation:** Ler as configurações de `process.env` em `config/`, sem valor padrão para segredos. Criar um `.env.example` com placeholders e trocar as chaves expostas. (Playbook T-01)

### [HIGH] Deprecated / Obsolete APIs and Dependencies — vulnerable dependency tree
- **ID:** AP-18
- **File:** `package.json:10-11`, `package-lock.json:641`, `package-lock.json:2021`
- **Description:** `npm audit --package-lock-only` encontra 12 vulnerabilidades: 1 critical, 7 high, 1 moderate e 3 low.
  - Por `sqlite3@5.1.7`: `tar` (critical, path traversal), `node-gyp`, `make-fetch-happen`, `cacache`, `brace-expansion` e `ip-address` (high).
  - Ainda por `sqlite3@5.1.7`: pacotes marcados `deprecated` no lockfile (`prebuild-install` "No longer maintained" em `package-lock.json:1573`, `tar`, `glob`, `inflight`, `rimraf`, `npmlog`).
  - Por `express@4.22.1`: `path-to-regexp@0.1.12` (high, ReDoS), `qs@6.14.2` (moderate, DoS) e `body-parser@1.20.4` (low).
- **Impact:** Há vulnerabilidades conhecidas de DoS no Express em runtime e de path traversal na cadeia de build nativo do sqlite3, além de pacotes sem manutenção.
- **Recommendation:** Rodar `npm audit fix` para aplicar os patches da linha Express 4.x, sem quebra. Avaliar `sqlite3@^6.0.1` (versão major), validando o build nativo no Node usado. (Playbook T-14)

### [HIGH] Tight Coupling Without Dependency Injection / No Composition Root
- **ID:** AP-08
- **File:** `src/AppManager.js:2`, `src/AppManager.js:5-8`, `src/app.js:5-14`
- **Description:** O construtor cria direto a dependência concreta `new sqlite3.Database(':memory:')` e a classe importa o singleton `config` de `./utils`. Além disso, `src/app.js` cria o app, chama `initDb()`, registra as rotas e executa `app.listen(config.port)` assim que o módulo é carregado, sem uma factory.
- **Impact:** Não dá para trocar o banco (arquivo, banco de teste) nem importar o app em testes sem abrir a porta 3000.
- **Recommendation:** Criar `createApp({ db, config })` para montar as dependências e deixar o `listen` só no entry point. (Playbook T-11)

### [HIGH] Broken Referential Integrity on Delete
- **ID:** AP-12
- **File:** `src/AppManager.js:14-15`, `src/AppManager.js:131-137`
- **Description:** `DELETE FROM users WHERE id = ?` apaga só o usuário. `enrollments.user_id` e `payments.enrollment_id` não têm `FOREIGN KEY` nem limpeza manual, e o `err` do callback é ignorado. A própria resposta admite o problema: "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.", e ela aparece até para um `id` que não existe.
- **Impact:** Depois de uma exclusão, o relatório financeiro mostra alunos `'Unknown'` (`src/AppManager.js:113`) com pagamentos órfãos.
- **Recommendation:** Apagar os pagamentos e as matrículas do usuário na mesma transação, tratar o erro e ajustar a mensagem. (Playbook T-17)

### [HIGH] Business Logic in Routes (fat controller)
- **ID:** AP-07
- **File:** `src/AppManager.js:28-78`, `src/AppManager.js:80-129`, `src/AppManager.js:131-137`
- **Description:** Os handlers fazem tudo inline:
  - O de checkout busca o curso e o usuário, cria o usuário e decide o pagamento com `cc.startsWith("4") ? "PAID" : "DENIED"`. Depois grava matrícula, pagamento e auditoria e chama `logAndCache`.
  - O do relatório soma `courseData.revenue += payment.amount` e monta a lista de alunos.
  - O de exclusão roda SQL direto.
- **Impact:** As regras de pagamento e de receita não podem ser reaproveitadas nem testadas sem subir o Express e o banco.
- **Recommendation:** Deixar os controllers finos e mover a lógica para `services/checkoutService` e `services/reportService`, com o SQL nos models. (Playbook T-03, T-13)

### [HIGH] Missing Input Validation
- **ID:** AP-14
- **File:** `src/AppManager.js:29-35`, `src/AppManager.js:46`, `src/AppManager.js:132`
- **Description:** O checkout só verifica se os campos existem (`if (!u || !e || !cid || !cc)`). Não confere tipo nem formato de `eml`, `c_id` ou `card`. Se `card` vier como número (`"card": 4111222233334444`), `cc.startsWith("4")` lança `TypeError` dentro do callback do sqlite3, onde o Express não captura o erro. O `:id` do DELETE também não é validado.
- **Impact:** Uma única requisição anônima com um tipo errado gera uma exceção não capturada que pode derrubar o processo inteiro (DoS). Por ser explorável remotamente sem autenticação, foi elevado para HIGH. Também permite gravar e-mails inválidos.
- **Recommendation:** Validar o body no controller: strings não vazias, e-mail válido, `c_id` inteiro positivo e `card` como string de dígitos. Responder 400 antes de chegar ao service. (Playbook T-12)

### [HIGH] Unprotected Destructive/Debug Endpoints and Broken Authentication — checkout ignores the password of existing accounts
- **ID:** AP-06
- **File:** `src/AppManager.js:40`, `src/AppManager.js:66-75`
- **Description:** O checkout procura o usuário só pelo e-mail (`SELECT id FROM users WHERE email = ?`). Se ele existe, chama `processPaymentAndEnroll(user.id)` sem comparar o `pwd` recebido com o hash salvo.
- **Impact:** Quem sabe o e-mail de alguém consegue criar matrículas e pagamentos na conta dessa pessoa, e o `audit_logs` registra a ação em nome dela.
- **Recommendation:** Verificar a senha antes de reutilizar uma conta existente. Isso muda o contrato (retornaria 401 para senha errada), então é uma decisão de produto. (Playbook T-06)

### [HIGH] Non-Atomic Multi-Step Writes (missing transaction)
- **ID:** AP-11
- **File:** `src/AppManager.js:50-61`, `src/AppManager.js:66-72`
- **Description:** Um checkout faz até quatro escritas encadeadas em callbacks, sem `BEGIN/COMMIT/ROLLBACK`: `INSERT INTO users` (69), `INSERT INTO enrollments` (50), `INSERT INTO payments` (54) e `INSERT INTO audit_logs` (57). O usuário é criado antes da decisão do pagamento (46-48).
- **Impact:** Um pagamento recusado deixa o usuário criado. Se o insert de pagamento falhar, a resposta é 500 mas a matrícula continua sem pagamento, ou seja, o aluno fica matriculado de graça. Erros na auditoria são ignorados.
- **Recommendation:** Decidir o pagamento antes de qualquer escrita e colocar as escritas numa transação dentro do service de checkout. (Playbook T-09)

### [HIGH] Mutable Global State
- **ID:** AP-09
- **File:** `src/utils.js:9-10`, `src/utils.js:12-15`, `src/utils.js:25`
- **Description:** `let globalCache = {}` é alterado por `logAndCache()` (`globalCache[key] = data`, chamado com `last_checkout_${userId}` em `src/AppManager.js:59`). Ele é exportado junto com `let totalRevenue = 0` via `module.exports`.
- **Impact:** O cache cresce sem limite (uma chave por usuário), nunca é lido, se perde a cada restart e não é compartilhado entre processos.
- **Recommendation:** Remover o estado global. Se um cache for mesmo necessário, injetá-lo pelo composition root. (Playbook T-11, T-18)

### [MEDIUM] Callback Hell / Pyramid of Doom
- **ID:** AP-17
- **File:** `src/AppManager.js:26`, `src/AppManager.js:37-77`, `src/AppManager.js:83-128`
- **Description:** O checkout aninha até seis callbacks: `db.get` curso → `db.get` usuário → `db.run` usuário → `db.run` matrícula → `db.run` pagamento → `db.run` auditoria. Por isso precisa de `const self = this`. O relatório controla o fim das consultas com contadores manuais `coursesPending--`/`enrPending--` e chama `res.json(report)` em três lugares (87, 98, 121).
- **Impact:** O fluxo é difícil de ler, é fácil responder duas vezes ou nunca responder, e os erros não se propagam naturalmente.
- **Recommendation:** Envolver o driver `sqlite3` em helpers com Promise e reescrever o fluxo com `async/await`. (Playbook T-10)

### [MEDIUM] Inadequate Middleware Usage / Inconsistent Responses
- **ID:** AP-19
- **File:** `src/AppManager.js:35`, `src/AppManager.js:38`, `src/AppManager.js:41`, `src/AppManager.js:48`, `src/AppManager.js:51`, `src/AppManager.js:55`, `src/AppManager.js:60`, `src/AppManager.js:70`, `src/AppManager.js:84`, `src/AppManager.js:135`
- **Description:** Cada handler monta sua própria resposta de erro, sem middleware comum. Os erros saem como texto puro (`res.status(400).send("Bad Request")`, `"Erro DB"`, `"Erro Matrícula"`, `"Pagamento recusado"`), o sucesso do checkout é JSON (`{ msg: "Sucesso", enrollment_id }`) e o DELETE responde em texto.
- **Impact:** As mensagens e os status de erro ficam espalhados e duplicados, e cada rota trata falhas de um jeito.
- **Recommendation:** Centralizar a tradução de erros em um middleware, mantendo os status e textos atuais que fazem parte do contrato. (Playbook T-07)

### [MEDIUM] Swallowed Errors / No Centralized Error Handler
- **ID:** AP-15
- **File:** `src/AppManager.js:38`, `src/AppManager.js:57`, `src/AppManager.js:92-93`, `src/AppManager.js:104-106`, `src/AppManager.js:133-135`, `src/app.js:5-10`
- **Description:**
  - `if (err || !course)` transforma um erro de banco em 404 "Curso não encontrado".
  - O `err` é ignorado na auditoria (57), nas consultas do relatório (92, 104, 106) e no DELETE (133).
  - Em 92-93, um erro deixa `enrollments` indefinido e `enrollments.length` lança `TypeError`.
  - `src/app.js` não registra nenhum middleware `(err, req, res, next)`.
- **Impact:** Falhas reais ficam invisíveis ou voltam com o status errado. Erros dentro dos callbacks derrubam o processo em vez de responder 500.
- **Recommendation:** Propagar os erros com `next(err)` a partir de handlers async e centralizar o tratamento em `middlewares/errorHandler`, com mensagem genérica. (Playbook T-07)

### [MEDIUM] N+1 Queries and Per-Row Aggregation
- **ID:** AP-13
- **File:** `src/AppManager.js:83`, `src/AppManager.js:89-92`, `src/AppManager.js:102-106`
- **Description:** O relatório roda `SELECT * FROM courses`. Para cada curso, roda `SELECT * FROM enrollments WHERE course_id = ?`. Para cada matrícula, roda mais `SELECT name, email FROM users WHERE id = ?` e `SELECT amount, status FROM payments WHERE enrollment_id = ?`, e soma a receita em JS.
- **Impact:** São 1 + C + 2·E consultas por requisição, então o tempo cresce junto com o número de matrículas.
- **Recommendation:** Usar uma única consulta com `LEFT JOIN` entre courses, enrollments, users e payments, e agrupar o resultado no model ou no service. (Playbook T-08)

### [LOW] Dead Code and Unused Imports
- **ID:** AP-22
- **File:** `src/AppManager.js:2`, `src/AppManager.js:104`, `src/utils.js:2-3`, `src/utils.js:5`, `src/utils.js:9-10`, `src/utils.js:25`
- **Description:** `totalRevenue` é importado e nunca usado. `globalCache` é exportado mas ninguém importa nem lê. `dbUser`, `dbPass` e `smtpUser` nunca são lidos. A coluna `email` de `SELECT name, email FROM users` é buscada e descartada.
- **Impact:** Ruído no código e a falsa impressão de que existem SMTP e autenticação no banco.
- **Recommendation:** Remover os imports, exports, chaves de config e colunas que não são usados. (Playbook T-16)

### [LOW] Poor Naming
- **ID:** AP-21
- **File:** `src/AppManager.js:4`, `src/AppManager.js:29-33`, `src/AppManager.js:89`, `src/AppManager.js:102`, `src/utils.js:12`, `src/utils.js:17`
- **Description:** Há variáveis como `u`, `e`, `p`, `cid`, `cc`, `c` e `enr`, e nomes genéricos como `AppManager`, `utils`, `logAndCache` e `badCrypto`. Os campos do body `usr`, `eml`, `pwd`, `c_id` e `card` fazem parte do contrato e precisam continuar iguais.
- **Impact:** O código fica mais lento de ler e a intenção fica obscura.
- **Recommendation:** No controller, mapear o body para nomes claros (`name`, `email`, `password`, `courseId`, `cardNumber`). (Playbook T-15)

### [LOW] Magic Numbers and Strings
- **ID:** AP-20
- **File:** `src/AppManager.js:7`, `src/AppManager.js:21`, `src/AppManager.js:46`, `src/AppManager.js:48`, `src/AppManager.js:108`, `src/utils.js:6`, `src/utils.js:19-22`
- **Description:** A regra de aprovação `cc.startsWith("4")` e os status `"PAID"`/`"DENIED"` aparecem repetidos como literais. `':memory:'` e `port: 3000` estão fixos no código, e `badCrypto` usa `10000`, `substring(0, 2)` e `substring(0, 10)`.
- **Impact:** Regras de negócio e configuração ficam escondidas em literais e podem divergir entre arquivos.
- **Recommendation:** Criar constantes nomeadas (`PAYMENT_STATUS`, `APPROVED_CARD_PREFIX`) e ler porta e caminho do banco de `config/`. (Playbook T-15)

### [LOW] Console Logging Instead of a Logger
- **ID:** AP-23
- **File:** `src/app.js:13`, `src/utils.js:13`
- **Description:** `console.log(`Frankenstein LMS rodando na porta ${config.port}...`)` e `console.log(`[LOG] Salvando no cache: ${key}`)` são usados sem níveis nem configuração. O log de `src/AppManager.js:45` está em AP-04.
- **Impact:** Não dá para filtrar ou silenciar logs por ambiente.
- **Recommendation:** Criar um logger simples com níveis em um único módulo. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `package.json:11`, `package-lock.json:2021` | `sqlite3@5.1.7`: traz `tar@6` (critical), `node-gyp`/`make-fetch-happen`/`cacache`/`brace-expansion`/`ip-address` (high) e pacotes `deprecated` no lockfile (`prebuild-install`, `glob`, `inflight`, `rimraf`, `npmlog`, `gauge`, `are-we-there-yet`, `@npmcli/move-file`) | `sqlite3@^6.0.1` (major; revalidar o build nativo) |
| `package.json:10`, `package-lock.json:641` | `express@4.22.1`: dependências transitivas vulneráveis `path-to-regexp@0.1.12` (high, ReDoS), `qs@6.14.2` (moderate, DoS), `body-parser@1.20.4` (low) | `npm audit fix` (patches da linha Express 4.x, sem quebra) |

```text
================================
Total: 21 findings
================================
```

O git mostra alterações não commitadas (`ecommerce-api-legacy/.claude/`). Recomendo fazer um commit ou backup antes da Fase 3.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
