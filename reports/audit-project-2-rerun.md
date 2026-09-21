# Audit Report — ecommerce-api-legacy (auditoria do código já refatorado, após o feedback da avaliação)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.4.0), gerada por `claude -p "/refactor-arch"` dentro de `ecommerce-api-legacy/`
> (modelo `claude-opus-5[1m]`, sessão `b48fad9d-89ac-4119-8da0-8f1719fc445e`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 1 · HIGH 1 · MEDIUM 3 · LOW 4 · Total 9.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.3
Files:   28 analyzed | ~666 lines of code
```

## Summary

CRITICAL: 1 | HIGH: 1 | MEDIUM: 3 | LOW: 4

## Findings

### [CRITICAL] Unprotected Destructive/Admin Endpoints — guarda opt-in, aberta por padrão
- **ID:** AP-06
- **File:** `src/middlewares/adminGuard.js:11-18`, `src/config/settings.js:21`, `src/app.js:15-17`, `src/views/routes.js:8-9`
- **Description:** `createAdminGuard` devolve um middleware que só chama `next()` quando `adminToken` é falsy (`adminGuard.js:13`), e o default de configuração é exatamente esse caso (`settings.js:21`: `adminToken: env.ADMIN_TOKEN || null`). Sem exportar `ADMIN_TOKEN`, `GET /api/admin/financial-report` e `DELETE /api/users/:id` (`routes.js:8-9`) ficam públicas — o próprio boot registra o aviso `'ADMIN_TOKEN não definido: as rotas administrativas continuam públicas.'` (`app.js:16`) e segue servindo. A comparação em si é correta (`crypto.timingSafeEqual` sobre digests SHA-256, `adminGuard.js:6-9`), mas é um token estático único, sem identidade nem rotação.
- **Impact:** Com o comando de execução documentado no README (`npm start`, sem variáveis), qualquer cliente anônimo lê o relatório financeiro completo (nome de todos os alunos + valores pagos, `financialReportModel.js:3-15`) e apaga qualquer usuário com suas matrículas e pagamentos (`userService.js:6-13`) — exposição de dados pessoais/financeiros e destruição de dados sem autenticação.
- **Recommendation:** Inverter o default: a guarda nega (403 com o envelope de erro atual) sempre que `ADMIN_TOKEN` não estiver configurado, e só libera quando a flag explícita **e** o token estiverem presentes, mantendo a comparação em tempo constante; a rota, o método e o status de sucesso continuam iguais. Isso é a exceção 2 de `mvc-guidelines.md` §9, que diz explicitamente que uma guarda "aberta quando a variável não está definida" não fecha o achado. (Playbook T-06)

### [HIGH] Missing Business-Rule Validation — checkout duplicado cobra e fatura duas vezes
- **ID:** AP-14
- **File:** `src/services/checkoutService.js:10-28`, `src/models/enrollmentModel.js:3-9`, `src/models/schema.js:18-22`
- **Description:** `checkout()` resolve o usuário por e-mail (`checkoutService.js:20-21`) e em seguida insere a matrícula sem nenhuma verificação de matrícula já existente (`checkoutService.js:22` → `enrollmentModel.create`). A tabela `enrollments` também não tem restrição de unicidade em `(user_id, course_id)` (`schema.js:18-22`), e `payments.enrollment_id UNIQUE` (`schema.js:25`) só impede dois pagamentos para a *mesma* matrícula — não para a mesma pessoa no mesmo curso.
- **Impact:** Repetir o mesmo `POST /api/checkout` (mesmo `eml` + mesmo `c_id`) autoriza o cartão novamente (`checkoutService.js:14`) e grava uma segunda matrícula e um segundo pagamento: o aluno é cobrado em duplicidade e o relatório financeiro soma a receita duas vezes e lista o aluno duas vezes (`financialReportModel.js:31-34`), corrompendo o número usado para decisão de negócio.
- **Recommendation:** Adicionar a regra no domínio: consultar a matrícula existente (`findByUserAndCourse`) antes de autorizar o pagamento e rejeitar com 400 (envelope de erro atual, exceção 6 de §9), reforçando com `UNIQUE (user_id, course_id)` em `enrollments` para fechar a corrida no nível do banco. (Playbook T-12, T-09)

### [MEDIUM] Inconsistent Response — delete de usuário inexistente responde sucesso
- **ID:** AP-14
- **File:** `src/controllers/userController.js:5-8`, `src/services/userService.js:6-13`, `src/models/userModel.js:19-22`
- **Description:** `userModel.deleteById` devolve `changes` (`userModel.js:21`) e `userService.deleteUser` propaga esse valor (`userService.js:11`), mas o controller descarta o retorno (`userController.js:6`: `await userService.deleteUser(req.params.id)`) e sempre responde `'Usuário deletado, junto com suas matrículas e pagamentos.'`. O `:id` também não passa por nenhum validador — `validateCheckoutInput` é o único validador do projeto (`src/utils/validators.js:17`) — então `DELETE /api/users/abc` executa a transação com três `DELETE` sem efeito e responde sucesso.
- **Impact:** Cliente e operador recebem confirmação de uma exclusão que não aconteceu (id inexistente, id não numérico ou id já removido), o que esconde erros de integração e falseia qualquer auditoria baseada na resposta; cada chamada inválida ainda abre uma transação e ocupa a fila única do banco.
- **Recommendation:** Validar o `:id` como inteiro positivo no controller e usar o `changes` retornado para responder 404 quando nada foi apagado, mantendo o corpo de sucesso atual. A mudança de 200 → 404 para um recurso inexistente é alteração de contrato (§9) e precisa de confirmação explícita; a validação do formato do id pode entrar já. (Playbook T-12, T-07)

### [MEDIUM] Performance — hash scrypt executado dentro da transação que serializa todo o banco
- **ID:** AP-13
- **File:** `src/models/userModel.js:10-17`, `src/services/checkoutService.js:17-27`, `src/models/database.js:25-56`
- **Description:** `userModel.create` faz `await hashPassword(password)` **antes** do `INSERT`, dentro da mesma função (`userModel.js:11-15`), e essa chamada acontece dentro de `db.transaction` (`checkoutService.js:17-21`). Como todas as operações do app passam por uma fila única (`database.js:29-33`, `enqueue`) e a transação segura essa fila do `BEGIN IMMEDIATE` ao `COMMIT` (`database.js:42-56`), o custo do KDF entra no caminho crítico global — medido nesta máquina: ~26 ms por hash com os parâmetros default do Node (`src/utils/password.js:9-13`).
- **Impact:** Cada checkout de usuário novo bloqueia **todas** as consultas da aplicação (inclusive o relatório financeiro e outros checkouts) pelo tempo do hash, além de manter a transação SQLite aberta mais tempo do que o necessário. O efeito cresce proporcionalmente se os parâmetros de custo do scrypt forem endurecidos, que é a recomendação de segurança.
- **Recommendation:** Calcular o hash fora da fronteira transacional (derivar a senha no service, antes de `db.transaction`, e passar o hash pronto ao model), mantendo o `INSERT` como única operação dentro da transação. (Playbook T-09, T-08)

### [MEDIUM] Non-atomic Operation — pagamento autorizado fora da transação, sem compensação
- **ID:** AP-11
- **File:** `src/services/checkoutService.js:14-27`
- **Description:** `paymentGateway.authorize` roda antes do `db.transaction` (`checkoutService.js:14` vs `:17`). Se qualquer escrita dentro da transação falhar, o `ROLLBACK` (`database.js:49`) desfaz apenas as linhas do banco; a autorização já concedida no gateway não é estornada nem registrada, e o cliente recebe 500 pelo handler central (`errorHandler.js:17-18`).
- **Impact:** Estado divergente entre o gateway e o banco: cobrança autorizada sem matrícula, sem pagamento gravado e sem entrada em `audit_logs` — invisível para o relatório financeiro e sem trilha para reconciliação. Hoje o gateway é simulado (`paymentGateway.js:11-13`), então o prejuízo é latente, mas a fronteira transacional é a de um gateway real.
- **Recommendation:** Tornar o efeito externo reversível/rastreável: registrar a intenção de pagamento antes de autorizar e, no `catch` do fluxo, chamar o void/refund do gateway (ou gravar o pagamento como pendente de estorno) antes de propagar o erro. (Playbook T-09)

### [LOW] Deprecated Dependency — `prebuild-install` (transitiva de sqlite3)
- **ID:** AP-18
- **File:** `package-lock.json:952`, `package.json:11`
- **Description:** Auditoria executada nesta sessão: `npm audit --package-lock-only` → **`found 0 vulnerabilities`**; a varredura de `"deprecated"` no lockfile retornou um único pacote, `prebuild-install@7.1.3` (`package-lock.json:952`: *"No longer maintained. Please contact the author of the relevant native addon"*), puxado por `sqlite3@6.0.1` (`package.json:11`). No código não há nenhuma API depreciada da tabela AP-18: não existem `new Buffer(`, `url.parse(`, `req.param(`, `res.sendfile(`, `body-parser` nem `querystring` (greps sem resultado), o JSON é parseado por `express.json()` (`createApp.js:20`) e os callbacks do driver já estão encapsulados em promises (`database.js:3-21`).
- **Impact:** Nenhum impacto em runtime — o pacote é usado apenas na instalação do binário nativo do sqlite3, não há vulnerabilidade conhecida e não existe versão corrigida do lado da dependência direta. É um risco de manutenção futura (build pode quebrar em versões novas de Node/npm).
- **Recommendation:** Manter apenas monitorado: acompanhar as releases do `sqlite3` e atualizar quando o driver trocar o mecanismo de download de binários; nenhuma mudança de dependência se justifica agora. (Playbook T-14)

### [LOW] Inconsistent Response Envelopes — JSON em duas rotas, texto puro nas outras
- **ID:** AP-19
- **File:** `src/controllers/userController.js:7`, `src/middlewares/errorHandler.js:3`, `src/middlewares/errorHandler.js:11-18`, `src/controllers/checkoutController.js:9`, `src/controllers/reportController.js:7`
- **Description:** Sucesso de checkout e relatório saem como JSON (`checkoutController.js:9`, `reportController.js:7`), enquanto o delete responde `text/html` com uma frase (`userController.js:7`) e **todos** os erros saem como texto puro (`errorHandler.js:3`, `:11`, `:12`, `:14`, `:18`). O próprio código documenta a escolha: *"Error bodies stay plain text, as in the original API"* (`errorHandler.js:5`).
- **Impact:** Cliente precisa de dois parsers e não tem campo de código de erro estável; qualquer automação sobre as respostas de erro depende de casar strings em português.
- **Recommendation:** Padronizar em um envelope JSON único para erro e sucesso. **Bloqueado por contrato**: `mvc-guidelines.md` §9 proíbe mudar envelope de resposta sem autorização do usuário — se a Fase 3 for aprovada, este item vai para "Remaining Items" a menos que você autorize a mudança. (Playbook T-07)

### [LOW] Dead Code — 5 models instanciados e nunca usados no composition root
- **ID:** AP-22
- **File:** `src/createApp.js:14`, `src/createApp.js:23`
- **Description:** `const models = createModels(db)` (`createApp.js:14`) constrói os seis models, mas o único consumo é `models.financialReport` (`createApp.js:23`) — grep de `models.` em `src/` retorna exatamente essa linha. Os demais (`users`, `courses`, `enrollments`, `payments`, `auditLogs`) são recriados pelos services a partir do handle correto (`checkoutService.js:6,18`, `userService.js:8`), então as instâncias do composition root são descartadas.
- **Impact:** Sugere ao leitor que o composition root distribui os models para as camadas, quando na prática cada service resolve os seus; alocação e acoplamento sem uso.
- **Recommendation:** Instanciar no composition root apenas o que é injetado (`createFinancialReportModel(db)`) e deixar `createModels` para os escopos de transação. (Playbook T-16)

### [LOW] Weak Password Policy — sem tamanho mínimo e seed com senha `123`
- **ID:** AP-05
- **File:** `src/utils/validators.js:21-31`, `src/models/schema.js:47`, `src/utils/password.js:9-13`
- **Description:** O armazenamento está correto (scrypt com salt aleatório de 16 bytes e chave de 64 bytes, formato `scrypt$salt$key`, `password.js:9-13`), mas a validação aceita qualquer string como `pwd`, sem tamanho mínimo (`validators.js:21`, `:31`); string vazia vira `null` e cria a conta **sem credencial** silenciosamente (`validators.js:31` → `userModel.js:11`). O seed cria o usuário `leonan@fullcycle.com.br` com a senha bem conhecida `'123'` (`schema.js:47`). Os parâmetros de custo do scrypt são os defaults do Node (N=16384), abaixo das recomendações atuais.
- **Impact:** Baixo hoje, porque não existe endpoint de autenticação que consuma esses hashes — nenhuma senha fraca é explorável pela API atual. Vira risco imediato no momento em que um login for adicionado.
- **Recommendation:** Exigir tamanho mínimo (≥ 8) no validador quando `pwd` for enviado, recusar string vazia explicitamente em vez de virar `null`, ler a senha do seed do ambiente (exceção 8 de §9) e elevar o custo do scrypt (N=2^17) junto com a introdução do login. (Playbook T-04, T-12)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `package-lock.json:952` (via `package.json:11`, `sqlite3@6.0.1`) | `prebuild-install@7.1.3` — marcado como *"No longer maintained"* no lockfile; usado só no build do binário nativo | Aguardar release do `sqlite3` que troque o download de binários; sem versão corrigida disponível hoje |

Checagem de código contra a tabela AP-18: nenhuma API depreciada em uso (`new Buffer(`, `url.parse(`, `crypto.createCipher(`, `fs.exists(`, `util.is*`, `req.param(`, `res.sendfile(`, `app.del()`, `body-parser`, `querystring`, `request`, `node-uuid` — todos sem ocorrência em `src/`). Auditoria de dependências: `npm audit --package-lock-only` → `found 0 vulnerabilities`.

```text
================================
Total: 9 findings
================================
```

O ponto central: o projeto **já está em MVC em camadas** (dependências apontando para baixo, SQL só nos models, erro centralizado, injeção via composition root), então não há achados de AP-01/02/03/07/08/09/10 — o que sobra é segurança de configuração (a guarda administrativa aberta por padrão, que é CRITICAL), uma regra de negócio ausente no checkout e ajustes de robustez/limpeza.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
