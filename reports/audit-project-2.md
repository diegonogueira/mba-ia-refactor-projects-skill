# Audit Report — ecommerce-api-legacy

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.2.0), gerada por `claude -p "/refactor-arch"` executado dentro de `ecommerce-api-legacy/`
> (modelo `claude-opus-5[1m]`, sessão `2deb3c3e-03a7-4bd2-8ae1-aa053d21e4be`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 5 · HIGH 7 · MEDIUM 5 · LOW 4 · Total 21.

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

CRITICAL: 5 | HIGH: 7 | MEDIUM: 5 | LOW: 4

## Findings

### [CRITICAL] God Class / God module
- **ID:** AP-03
- **File:** `src/AppManager.js:4-139`
- **Description:** A classe `AppManager` acumula todas as responsabilidades da aplicação: cria a conexão (`new sqlite3.Database(':memory:')`), gera o schema e o seed em `initDb()`, registra as 3 rotas em `setupRoutes(app)`, executa SQL direto nos handlers e implementa regras de negócio (aprovação de pagamento `cc.startsWith("4")`, soma de receita `courseData.revenue += payment.amount`), além de auditoria e cache.
- **Impact:** Nada pode ser testado isoladamente. Qualquer mudança em usuários, matrículas/pagamentos ou relatórios mexe na mesma classe, e trocar o banco ou o gateway exige reescrever tudo.
- **Recommendation:** Separar em `config/`, `models/` (User, Course, Enrollment, Payment, AuditLog), `services/` (checkout), `controllers/`, `routes/`, e um módulo de banco com schema/seed. (Playbook T-03)

### [CRITICAL] Insecure password storage
- **ID:** AP-05
- **File:** `src/AppManager.js:18`, `src/AppManager.js:68-69`, `src/utils.js:17-23`
- **Description:** `badCrypto(pwd)` concatena 10000 vezes os 2 primeiros caracteres de `Buffer.from(pwd).toString('base64')` e devolve `hash.substring(0, 10)`. O "hash" é só esse par repetido (ex.: `"senhaforte"` → `"c2c2c2c2c2"`), sem sal e determinístico. Sem `pwd`, a senha padrão é `"123456"` (`badCrypto(p || "123456")`). O seed grava a senha do usuário Leonan em texto puro (`'123'`).
- **Impact:** O valor salvo revela o início da senha e causa colisões em massa: toda senha que começa com "se" vira o mesmo "hash". Contas criadas sem senha ficam com uma senha previsível, e um vazamento do banco expõe credenciais.
- **Recommendation:** Usar `crypto.scrypt` (nativo do Node) com sal aleatório por usuário, ou bcrypt/argon2. Nunca usar senha padrão fixa. (Playbook T-04)

### [CRITICAL] Sensitive data exposure (responses and logs)
- **ID:** AP-04
- **File:** `src/AppManager.js:45`
- **Description:** `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava no log, a cada checkout, o número completo do cartão (`card`) e a chave live do gateway (`pk_live_...`).
- **Impact:** Viola o PCI-DSS. Quem acessa os logs (agregador, CI, suporte) obtém números de cartão e a chave de produção do gateway.
- **Recommendation:** Não logar número de cartão nem segredos. Se precisar, logar só o cartão mascarado (`****4444`) com um logger. (Playbook T-05)

### [CRITICAL] Unprotected destructive/debug endpoints and broken authentication
- **ID:** AP-06
- **File:** `src/AppManager.js:80-129`, `src/AppManager.js:131-137`
- **Description:** `DELETE /api/users/:id` executa `DELETE FROM users WHERE id = ?`, e `GET /api/admin/financial-report` devolve a receita por curso com nomes de alunos e valores pagos. Nenhuma das duas rotas tem autenticação ou autorização: nenhum middleware é registrado antes de `manager.setupRoutes(app)`.
- **Impact:** Qualquer cliente anônimo apaga usuários (e ainda corrompe matrículas/pagamentos, ver AP-12) e lê dados financeiros e pessoais de alunos.
- **Recommendation:** Criar um middleware de guarda para rotas administrativas/destrutivas (ex.: token de admin vindo de variável de ambiente). (Playbook T-06)

### [CRITICAL] Hardcoded credentials and secrets
- **ID:** AP-01
- **File:** `src/utils.js:2-5`
- **Description:** O objeto `config` traz literais `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser: "no-reply@fullcycle.com.br"`. A chave do gateway ainda aparece no log (ver AP-04).
- **Impact:** Segredos de produção ficam no repositório e no histórico do git, acessíveis a qualquer pessoa com acesso ao código. Trocar uma credencial exige um novo deploy.
- **Recommendation:** Criar `config/` lendo `process.env` sem valores secretos padrão, adicionar `.env.example` com placeholders e trocar as credenciais expostas. (Playbook T-01)

### [HIGH] Deprecated / Vulnerable Dependencies — Express runtime chain
- **ID:** AP-18
- **File:** `package.json:10`, `package-lock.json:228`, `package-lock.json:1563`, `package-lock.json:1640`
- **Description:** `npm audit --package-lock-only` aponta falhas em pacotes que `express@4.22.1` usa em tempo de execução:
  - `path-to-regexp@0.1.12` (high, ReDoS com vários parâmetros de rota, GHSA-37ch-88jc-xwx2);
  - `qs@6.14.2` (moderate, DoS, GHSA-q8mj-m7cp-5q26, GHSA-x5fp-wj9c-mxmx, GHSA-4mjr-xmp4-gh2g);
  - `body-parser@1.20.4` (low, GHSA-v422-hmwv-36x6).

  Na verificação de código não apareceu nenhuma API depreciada de Node/Express: `Buffer.from`, `express.json()` e `app.delete` já são as formas atuais.
- **Impact:** Requisições HTTP forjadas, sem autenticação, podem esgotar CPU/memória e derrubar a API (DoS).
- **Recommendation:** Atualizar sem sair da major 4 (`npm audit fix`, sem breaking change; `latest-4` = `express@4.22.3`) e regenerar o lockfile. (Playbook T-14)

### [HIGH] Tight coupling without dependency injection / no composition root
- **ID:** AP-08
- **File:** `src/AppManager.js:7`, `src/app.js:5-14`
- **Description:** O construtor de `AppManager` cria a dependência concreta `new sqlite3.Database(':memory:')` e importa `config` direto de `./utils`. Já `src/app.js`, no próprio carregamento do módulo, cria o `express()`, instancia o manager, roda `initDb()` e chama `app.listen(config.port)`. Não existe factory (`createApp`) nem injeção do banco.
- **Impact:** Não dá para testar rotas ou regras com banco falso, nem importar o app sem subir o servidor. Trocar o SQLite exige reescrever a classe.
- **Recommendation:** Criar uma factory `createApp({ db })` e um módulo de conexão, com models recebendo `db` por parâmetro. `src/app.js` fica só com a montagem e o `listen`. (Playbook T-11)

### [HIGH] Non-atomic multi-step writes (missing transaction)
- **ID:** AP-11
- **File:** `src/AppManager.js:12`, `src/AppManager.js:40`, `src/AppManager.js:50-61`, `src/AppManager.js:69-71`
- **Description:** O checkout grava em sequência `users` → `enrollments` → `payments` → `audit_logs`, em callbacks aninhados e sem `BEGIN/COMMIT/ROLLBACK`. Se o `INSERT INTO payments` falhar, a resposta é `500 "Erro Pagamento"`, mas a matrícula e o usuário recém-criado ficam gravados. Além disso, o fluxo `SELECT id FROM users WHERE email = ?` → `INSERT INTO users` não tem apoio de uma restrição `UNIQUE` em `users.email`.
- **Impact:** Matrícula sem pagamento (acesso grátis ao curso), usuários duplicados em checkouts simultâneos e trilha de auditoria incompleta.
- **Recommendation:** Rodar o caso de uso numa única transação (`BEGIN IMMEDIATE` … `COMMIT`/`ROLLBACK`) dentro de um service de checkout e adicionar `UNIQUE` em `users.email`. (Playbook T-09)

### [HIGH] Broken referential integrity on delete
- **ID:** AP-12
- **File:** `src/AppManager.js:14-15`, `src/AppManager.js:133-135`
- **Description:** `DELETE FROM users WHERE id = ?` apaga só o usuário. `enrollments.user_id` e `payments.enrollment_id` não têm `FOREIGN KEY`/`ON DELETE CASCADE`, nem há limpeza manual. A própria resposta admite: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."`. O `err` do callback também é ignorado.
- **Impact:** O relatório financeiro passa a listar alunos como `'Unknown'` e ainda soma a receita de pagamentos órfãos. A inconsistência é permanente.
- **Recommendation:** Tratar os registros filhos na mesma transação do delete, ou declarar as FKs com `PRAGMA foreign_keys = ON`. (Playbook T-17)

### [HIGH] Business logic in routes/controllers (fat controller)
- **ID:** AP-07
- **File:** `src/AppManager.js:28-78`, `src/AppManager.js:80-129`
- **Description:** O handler de `POST /api/checkout` tem 51 linhas: valida a entrada, busca curso e usuário, cria usuário com hash, decide a aprovação do pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`) e grava matrícula, pagamento, auditoria e cache. O handler de `GET /api/admin/financial-report` tem 50 linhas e monta a agregação de receita (`courseData.revenue += payment.amount` quando `status === 'PAID'`) direto com SQL.
- **Impact:** As regras de pagamento e de receita não podem ser reaproveitadas nem testadas sem HTTP e banco. Mudar o gateway ou o cálculo obriga a mexer na rota.
- **Recommendation:** Controllers finos que chamam um service de checkout e um model/relatório. A regra de aprovação fica isolada num gateway de pagamento. (Playbook T-03, T-13)

### [HIGH] Missing or inconsistent input validation
- **ID:** AP-14
- **File:** `src/AppManager.js:29-35`, `src/AppManager.js:46`
- **Description:** A única validação é `if (!u || !e || !cid || !cc)`, sem checar tipo nem formato. Um `card` numérico (`"card": 4111222233334444`) chega a `cc.startsWith("4")`, que lança `TypeError` dentro do callback do sqlite3, fora do fluxo do Express. Isso vira uma exceção não capturada que encerra o processo. `eml` não é validado como e-mail e `c_id` não é validado como inteiro.
- **Impact:** Uma única requisição anônima pode derrubar a API inteira (DoS), e dados malformados são gravados.
- **Recommendation:** Validar no controller (strings obrigatórias, e-mail, `c_id` inteiro, cartão só com dígitos) e responder 400 antes de tocar no banco. (Playbook T-12)

### [HIGH] Mutable global state
- **ID:** AP-09
- **File:** `src/AppManager.js:59`, `src/utils.js:9-10`, `src/utils.js:14`, `src/utils.js:25`
- **Description:** `let globalCache = {}` e `let totalRevenue = 0` são estado mutável exportado pelo módulo. `logAndCache()` grava `globalCache[\`last_checkout_${userId}\`]` a cada checkout e nunca lê nem remove essas entradas.
- **Impact:** A memória cresce com o número de usuários. O estado se perde no restart, não é compartilhado entre instâncias e cria um efeito colateral escondido que atrapalha testes.
- **Recommendation:** Remover o cache global, que ninguém lê. Se for necessário, usar um cache com limite/TTL injetado pela factory da aplicação. (Playbook T-11, T-18)

### [MEDIUM] Deprecated / Vulnerable Dependencies — sqlite3 build chain
- **ID:** AP-18
- **File:** `package.json:11`, `package-lock.json:1437`, `package-lock.json:1569`, `package-lock.json:2113`
- **Description:** 9 das 12 vulnerabilidades do `npm audit` vêm do `sqlite3@5.1.7`:
  - `tar@6.2.1` (critical, path traversal/sobrescrita de arquivos, ex.: GHSA-34x7-hfp2-rc4v; também marcado como deprecated);
  - pelo `node-gyp@8.4.1` opcional: `make-fetch-happen`, `cacache`, `http-proxy-agent`, `@tootallnate/once`, `ip-address` e `brace-expansion` (high/low).

  O lockfile também marca como deprecated `prebuild-install@7.1.3`, `glob@7.2.3`, `inflight@1.0.6`, `rimraf@3.0.2`, `npmlog@6.0.2`, `gauge@4.0.4`, `are-we-there-yet@3.0.1` e `@npmcli/move-file@1.1.2`.
- **Impact:** O risco está na instalação/compilação do binário nativo (extração de tarballs), não nas requisições. Pacotes sem suporte dificultam a manutenção.
- **Recommendation:** Avaliar a migração para `sqlite3@6.0.1` (major; exige Node ≥ 20.17; traz `node-gyp` 12.x e `tar` ^7.5.10), validando com smoke test. (Playbook T-14)

### [MEDIUM] Callback hell / pyramid of doom
- **ID:** AP-17
- **File:** `src/AppManager.js:26`, `src/AppManager.js:37-77`, `src/AppManager.js:83-128`
- **Description:** O checkout aninha 5 callbacks de banco (`db.get` curso → `db.get` usuário → `db.run` matrícula → `db.run` pagamento → `db.run` auditoria) e precisa de `const self = this` para chegar ao banco dentro de `function(err)`. O relatório controla o fim do processamento com contadores manuais `coursesPending--` / `enrPending--`.
- **Impact:** O fluxo é difícil de ler e de tratar erros (resposta duplicada ou nunca enviada), e é a origem dos problemas de AP-11 e AP-15.
- **Recommendation:** Envolver o driver com promises e usar `async/await`. (Playbook T-10)

### [MEDIUM] Inadequate middleware usage / inconsistent responses
- **ID:** AP-19
- **File:** `src/AppManager.js:35`, `src/AppManager.js:38`, `src/AppManager.js:41`, `src/AppManager.js:48`, `src/AppManager.js:51`, `src/AppManager.js:55`, `src/AppManager.js:70`, `src/AppManager.js:84`, `src/AppManager.js:135`
- **Description:** Erros respondem texto puro com mensagens avulsas (`res.status(400).send("Bad Request")`, `send("Erro DB")`, `send("Erro Matrícula")`). Sucessos respondem JSON (`res.status(200).json({ msg: "Sucesso", enrollment_id: enrId })`), mas o DELETE responde texto. O tratamento de erro se repete em cada callback, sem middleware.
- **Impact:** O cliente precisa lidar com formatos diferentes por rota e status, e o tratamento de erro fica duplicado.
- **Recommendation:** Criar um middleware de erro central e helpers de resposta, mantendo os status e corpos do contrato. (Playbook T-07)

### [MEDIUM] Swallowed / generic exception handling, no centralized error handler
- **ID:** AP-15
- **File:** `src/AppManager.js:38`, `src/AppManager.js:57`, `src/AppManager.js:92-93`, `src/AppManager.js:104-106`, `src/AppManager.js:133-135`, `src/app.js:5-10`
- **Description:** Erros do driver são ignorados ou disfarçados:
  - uma falha de banco na busca do curso vira `404 "Curso não encontrado"` (`if (err || !course)`);
  - o `err` do insert em `audit_logs` é ignorado;
  - no relatório, `(err, enrollments)` não é checado e `enrollments.length` lança `TypeError` se a query falhar; `(err, user)` e `(err, payment)` também são ignorados;
  - o DELETE ignora `err` e responde sucesso mesmo quando falha;
  - `src/app.js` não registra um middleware de erro `(err, req, res, next)`.
- **Impact:** Falhas silenciosas (auditoria perdida, deleção "bem-sucedida" que não aconteceu), diagnóstico errado e risco de derrubar o processo.
- **Recommendation:** Propagar os erros (`async/await` + `next(err)`) até um handler central que loga e responde 500. (Playbook T-07)

### [MEDIUM] N+1 queries and per-row aggregation
- **ID:** AP-13
- **File:** `src/AppManager.js:89-92`, `src/AppManager.js:102-106`
- **Description:** `GET /api/admin/financial-report` busca todos os cursos e roda `SELECT * FROM enrollments WHERE course_id = ?` para cada um. Para cada matrícula roda ainda `SELECT name, email FROM users WHERE id = ?` e `SELECT amount, status FROM payments WHERE enrollment_id = ?`. São 1 + C + 2·E queries, com a receita somada em JavaScript.
- **Impact:** O tempo de resposta cresce com o número de matrículas (10 mil matrículas ≈ 20 mil queries).
- **Recommendation:** Uma única query com `LEFT JOIN` entre courses, enrollments, users e payments, com a agregação feita no model. (Playbook T-08)

### [LOW] Dead code and unused imports/dependencies
- **ID:** AP-22
- **File:** `src/AppManager.js:2`, `src/AppManager.js:104`, `src/utils.js:2-3`, `src/utils.js:5`, `src/utils.js:9-10`, `src/utils.js:25`
- **Description:** Há código sem uso:
  - `totalRevenue` é importado e exportado, mas nunca usado;
  - `globalCache` é exportado e só recebe escrita, nunca leitura;
  - as chaves `dbUser`, `dbPass` e `smtpUser` do `config` nunca são lidas (o SQLite em memória não usa usuário/senha e não há envio de e-mail);
  - a coluna `email` é selecionada em `SELECT name, email FROM users` e não é usada.
- **Impact:** Ruído que confunde quem lê (sugere SMTP e credenciais de banco que não existem) e mantém segredos desnecessários no código.
- **Recommendation:** Remover os imports, exports e chaves de configuração sem uso. (Playbook T-16)

### [LOW] Magic numbers and strings
- **ID:** AP-20
- **File:** `src/AppManager.js:7`, `src/AppManager.js:21`, `src/AppManager.js:46`, `src/AppManager.js:48`, `src/AppManager.js:68`, `src/AppManager.js:108`, `src/utils.js:6`, `src/utils.js:19`
- **Description:** Literais soltos pelo código: caminho do banco `':memory:'`, prefixo de aprovação `"4"`, status `"PAID"`/`"DENIED"` repetidos (inclusive no seed), senha padrão `"123456"`, porta `3000` fixa e `10000` iterações em `badCrypto`.
- **Impact:** Regras de negócio escondidas em literais; mudar um status ou a porta exige procurar pelo código todo.
- **Recommendation:** Constantes com nome (ex.: `PAYMENT_STATUS.PAID`) e configuração por ambiente (`PORT`, `DB_PATH`). (Playbook T-15)

### [LOW] Poor naming
- **ID:** AP-21
- **File:** `src/AppManager.js:29-33`, `src/AppManager.js:89`, `src/AppManager.js:102`, `src/utils.js:17`
- **Description:** Variáveis curtas `u`, `e`, `p`, `cid`, `cc` para usuário, e-mail, senha, curso e cartão; `c` e `enr` nos loops do relatório. A função `badCrypto` e os nomes genéricos `utils` e `AppManager` não dizem qual é a responsabilidade.
- **Impact:** Leitura lenta e sujeita a erro (`e` costuma significar erro).
- **Recommendation:** Nomes descritivos internamente (`name`, `email`, `password`, `courseId`, `cardNumber`). Os campos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) são convertidos só no controller. (Playbook T-15)

### [LOW] print/console logging instead of a logger
- **ID:** AP-23
- **File:** `src/app.js:13`, `src/utils.js:13`
- **Description:** `console.log` é usado como log da aplicação (`"Frankenstein LMS rodando na porta ..."`, `"[LOG] Salvando no cache: ..."`), sem níveis nem configuração. O log com cartão e chave (`src/AppManager.js:45`) foi classificado como AP-04.
- **Impact:** Não dá para filtrar por nível nem silenciar em testes, e os logs não são estruturados.
- **Recommendation:** Um logger simples com níveis (`info`/`error`) configurado em `config/`. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `package-lock.json:1563` | `path-to-regexp@0.1.12` (via `express@4.22.1`): ReDoS GHSA-37ch-88jc-xwx2 (high) | `path-to-regexp@0.1.13` via `npm audit fix` (`express@4.22.3`) |
| `package-lock.json:1640` | `qs@6.14.2`: DoS GHSA-q8mj-m7cp-5q26, GHSA-x5fp-wj9c-mxmx, GHSA-4mjr-xmp4-gh2g (moderate) | Versão corrigida via `npm audit fix` |
| `package-lock.json:228` | `body-parser@1.20.4`: GHSA-v422-hmwv-36x6 (low) | `body-parser@>=1.20.6` via `npm audit fix` |
| `package-lock.json:2113` | `tar@6.2.1` (via `sqlite3@5.1.7`): várias falhas critical de path traversal; deprecated | `sqlite3@6.0.1` (depende de `tar` ^7.5.10) |
| `package-lock.json:1437` | `node-gyp@8.4.1` (opcional do `sqlite3`) → `make-fetch-happen`, `cacache`, `http-proxy-agent`, `@tootallnate/once`, `ip-address`, `brace-expansion` (high/low) | `sqlite3@6.0.1` (usa `node-gyp` 12.x) |
| `package-lock.json:1569` | `prebuild-install@7.1.3`: deprecated ("No longer maintained") | Sem substituto direto (o `sqlite3@6.0.1` ainda usa); acompanhar o upstream |
| `package-lock.json:33`, `package-lock.json:160`, `package-lock.json:763`, `package-lock.json:827`, `package-lock.json:1074`, `package-lock.json:1478`, `package-lock.json:1718` | `@npmcli/move-file@1.1.2`, `are-we-there-yet@3.0.1`, `gauge@4.0.4`, `glob@7.2.3`, `inflight@1.0.6`, `npmlog@6.0.2`, `rimraf@3.0.2`: deprecated, vindos da cadeia opcional do `node-gyp@8` | Atualizar `sqlite3` e, com ele, `node-gyp` |

```text
================================
Total: 21 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
