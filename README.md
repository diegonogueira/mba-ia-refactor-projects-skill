# Refatoração Arquitetural Automatizada com a Skill `refactor-arch`

Entrega do desafio **Criação de Skills — Refatoração Arquitetural Automatizada** (MBA IA). O enunciado original está preservado em [`docs/ENUNCIADO.md`](docs/ENUNCIADO.md).

A skill `refactor-arch` (Claude Code) analisa uma codebase, audita anti-patterns com severidade e `arquivo:linha`, pede confirmação e refatora o projeto para MVC, validando que a aplicação continua de pé e que todos os endpoints originais respondem.

## Sumário

- [A) Análise Manual](#a-análise-manual)
- [B) Construção da Skill](#b-construção-da-skill)
- [C) Resultados](#c-resultados)
- [D) Como Executar](#d-como-executar)

---

## A) Análise Manual

Antes de escrever a skill, li integralmente o código dos três projetos, subi cada aplicação e exercitei todos os endpoints (script em [`scripts/smoke_test.py`](scripts/smoke_test.py)). Os problemas abaixo foram confirmados lendo o código e, quando possível, **reproduzidos com requisições reais** contra a versão original. As linhas referem-se ao código original (commit `6d1ce62`).

Escala usada (definida no enunciado): **CRITICAL** — segurança/arquitetura grave; **HIGH** — violação forte de MVC/SOLID; **MEDIUM** — padronização, duplicação, performance moderada, validação; **LOW** — legibilidade, nomes, magic numbers.

### Projeto 1 — `code-smells-project` (Python/Flask, API de E-commerce)

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection** em praticamente todas as queries (concatenação de strings) | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 149-151, 155-166, 174, 188, 192, 220, 224, 279-281, 289-297` | Reproduzido: `POST /login` com `email = "' OR 1=1 --"` autentica como **Admin**; `GET /produtos/busca?q=' OR '1'='1` devolve a tabela inteira. Permite ler/alterar qualquer dado. |
| 2 | CRITICAL | **Endpoints administrativos sem autenticação** que executam SQL arbitrário e apagam o banco | `app.py:47-57` (`/admin/reset-db`), `app.py:59-78` (`/admin/query`) | Qualquer cliente anônimo pode executar `DROP`/`DELETE` ou zerar todas as tabelas com um `POST`. É um backdoor. |
| 3 | CRITICAL | **Credenciais hardcoded e expostas** | `app.py:7` (`SECRET_KEY`), `controllers.py:285-289` (`/health` devolve `secret_key`, `db_path`, `debug`) | A chave que assina sessões está no repositório **e** é devolvida publicamente pelo health check — qualquer um pode forjar sessões. |
| 4 | CRITICAL | **Senhas em texto puro**, comparadas via SQL e **devolvidas na API** | `database.py:75-83` (seed), `models.py:105-120` (login), `models.py:79-86` e `95-102` (`senha` no dict), `controllers.py:128-144` (`GET /usuarios`) | `GET /usuarios` lista e-mail e senha de todos os usuários. Vazamento total de credenciais. |
| 5 | CRITICAL | **God modules / sem separação de camadas** | `models.py:1-314`, `controllers.py:1-292`, `app.py:47-78` | `models.py` mistura acesso a dados, regra de pedido/estoque e regra de desconto de 4 domínios; `controllers.py` mistura validação, "notificações" e HTTP; `app.py` tem rota com SQL direto. Impossível testar isoladamente. |
| 6 | HIGH | **Debug ligado e bind em `0.0.0.0`** | `app.py:8`, `app.py:88` | O debugger do Werkzeug exposto na rede permite execução de código; stack traces vazam detalhes internos. |
| 7 | HIGH | **Regra de negócio em lugar errado + efeitos colaterais inline** | `models.py:133-169` (criação de pedido), `models.py:256-262` (faixas de desconto), `controllers.py:208-210` e `247-250` (e-mail/SMS/push simulados com `print`) | Regras de negócio espalhadas entre "model" e "controller"; não há camada de serviço para notificações. |
| 8 | HIGH | **Estado global mutável / acoplamento sem DI** | `database.py:4-11` (`global db_connection`, `check_same_thread=False`), imports diretos de `get_db` em `models.py:1`, `controllers.py:3`, `app.py:4` | Uma única conexão compartilhada entre threads, sem injeção de dependência — difícil testar e sujeito a condições de corrida. |
| 9 | HIGH | **Pedido não atômico / validação de itens ausente** | `models.py:139-168`, `controllers.py:195-201` | Reproduzido: pedido com `quantidade: -5` retorna 201 com total negativo e **aumenta** o estoque (10 → 15). Checagem e baixa de estoque separadas permitem overselling concorrente. |
| 10 | MEDIUM | **Queries N+1** | `models.py:171-201` e `203-233` | 1 query de pedidos + 1 por pedido (itens) + 1 por item (nome do produto). Cresce linearmente com o volume. |
| 11 | MEDIUM | **Código duplicado** | `models.py:12-21 / 31-40 / 304-313` (mapeamento de produto), `models.py:171-201` ≈ `203-233`, `controllers.py:28-50` ≈ `72-90` | A mesma regra precisa ser corrigida em vários lugares (ex.: validação de categoria existe no create mas não no update). |
| 12 | MEDIUM | **Validação ausente → 500** | `controllers.py:43-46` (`preco < 0` com string), `controllers.py:169-171` e `239-240` (`dados.get` com corpo `None`), `controllers.py:81-92` (categoria não validada no update) | Reproduzido: `POST /produtos` com `"preco": "10"` → 500 `'<' not supported between instances of 'str' and 'int'`. |
| 13 | MEDIUM | **Tratamento de erro genérico que vaza exceção** e nenhum handler central | `controllers.py:10-12, 21-22, 60-62, 95-96, …` (16 blocos `except Exception as e: return jsonify({"erro": str(e)}), 500`) | Mensagens internas vão para o cliente; código repetido em cada handler. |
| 14 | MEDIUM | **CORS aberto para qualquer origem** | `app.py:9` | Middleware configurado sem `origins`, somado à ausência de autenticação. |
| 15 | LOW | **`print` como log** (inclusive de e-mails) | `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250`, `app.py:56, 83-86` | Sem níveis de log; dados pessoais no stdout. |
| 16 | LOW | **Magic numbers/strings** | `models.py:257-262` (10000/5000/1000, 0.1/0.05/0.02), `controllers.py:47-52` (2, 200, lista de categorias), `controllers.py:242` (status), `app.py:88` (porta) | Regras de negócio sem nome, repetidas e difíceis de alterar. |
| 17 | LOW | **Imports não usados / nomes ruins** | `models.py:2` (`sqlite3`), `database.py:2` (`os`); parâmetro `id` sombreando builtin em `models.py:24, 54, 65, 89` e `controllers.py:14, 56, 160` | Ruído e risco de bugs sutis. |

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express, LMS com checkout)

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded** (senha de banco, chave de gateway `pk_live_…`, usuário SMTP) | `src/utils.js:1-7` | Segredos de produção versionados; qualquer pessoa com acesso ao repositório pode usá-los. |
| 2 | CRITICAL | **Número de cartão e chave do gateway em log** | `src/AppManager.js:45` | Violação de PCI-DSS: dados de cartão completos e segredo em texto puro no stdout. |
| 3 | CRITICAL | **God Class `AppManager`** | `src/AppManager.js:4-139` | Uma classe cria conexão, schema, seed, registra rotas, valida entrada, processa pagamento, matrícula, auditoria e relatório financeiro. |
| 4 | CRITICAL | **Hash de senha caseiro e quebrado** + senha padrão | `src/utils.js:17-23` (`badCrypto`), `src/AppManager.js:68` (`p \|\| "123456"`), `src/AppManager.js:18` (seed com `'123'` em claro) | Reproduzido: `badCrypto("senhaforte") === badCrypto("se123") === "c2c2c2c2c2"` — só os 2 primeiros caracteres base64 importam, colisões triviais e reversível. |
| 5 | HIGH | **Checkout não atômico** (matrícula, pagamento e auditoria em inserts independentes) | `src/AppManager.js:50-63` | Se o insert de pagamento falhar, a matrícula fica gravada sem pagamento; erro do audit log é ignorado (linha 57). |
| 6 | HIGH | **Regra de negócio e pagamento dentro da rota** (fat controller) | `src/AppManager.js:28-78` (aprovação `cc.startsWith("4")` na linha 46) | Impossível testar o fluxo de checkout sem HTTP e banco; não há camada de serviço. |
| 7 | HIGH | **Estado global mutável** | `src/utils.js:9-15` (`globalCache`, `totalRevenue` exportados), `src/AppManager.js:59` | Cache cresce sem limite (vazamento de memória) e é compartilhado por toda a aplicação. |
| 8 | HIGH | **Endpoints administrativos/destrutivos sem autenticação e exclusão que corrompe dados** | `src/AppManager.js:80` (relatório financeiro), `src/AppManager.js:131-137` (`DELETE /api/users/:id` deixa matrículas/pagamentos órfãos e ignora `err`) | Reproduzido: após `DELETE /api/users/1` o relatório passa a exibir `"student": "Unknown"` — a própria resposta admite dados sujos. |
| 9 | HIGH | **Acoplamento sem injeção de dependência** | `src/AppManager.js:7` (`new sqlite3.Database(':memory:')` no construtor), `src/app.js:8-10` | Banco concreto instanciado dentro da classe; não é possível trocar/mocar. |
| 10 | MEDIUM | **N+1 no relatório financeiro** + contadores manuais | `src/AppManager.js:83-128` | 1 query de cursos + 1 por curso + 2 por matrícula; erros (`err`) ignorados nas linhas 92, 104 e 106 derrubam o processo se a query falhar. |
| 11 | MEDIUM | **Callback hell** (5 níveis) | `src/AppManager.js:37-77` | Fluxo ilegível, tratamento de erro duplicado a cada nível, `self = this` (linha 26). |
| 12 | MEDIUM | **Validação de entrada insuficiente** | `src/AppManager.js:35` | Não valida formato de e-mail, cartão ou `c_id`; senha é opcional. |
| 13 | MEDIUM | **Respostas e erros inconsistentes** | `src/AppManager.js:35, 38, 41, 48, 51, 55, 135` | Mistura texto puro (`"Bad Request"`, `"Erro DB"`) com JSON; nenhum middleware de erro. |
| 14 | MEDIUM | **Dependências obsoletas/vulneráveis** | `package.json:10-11`, `package-lock.json` | `npm install` emite avisos de `deprecated` (`inflight`, `glob@7`, `rimraf@3`, `tar@6`, `npmlog`…) vindos do `sqlite3@5`; `npm audit` aponta 12 vulnerabilidades (1 critical, 7 high). |
| 15 | LOW | **Nomes crípticos** | `src/AppManager.js:29-33` (`u, e, p, cid, cc`), campos `usr/eml/pwd/c_id` | Dificulta leitura; campos do contrato precisam ser mantidos, mas internamente devem ter nomes claros. |
| 16 | LOW | **Magic numbers/strings** | `src/utils.js:19` (10000), `src/AppManager.js:46` (`"4"`), `'PAID'/'DENIED'` repetidos, `src/utils.js:6` (porta) | Regras implícitas e espalhadas. |
| 17 | LOW | **Código morto** | `src/utils.js:10` (`totalRevenue`), `src/AppManager.js:2` (import não usado), `src/utils.js:2-3, 5` (`dbUser`, `dbPass`, `smtpUser` nunca lidos) | Ruído e falsa impressão de funcionalidade. |
| 18 | LOW | **`console.log` como log** | `src/AppManager.js:45`, `src/utils.js:13`, `src/app.js:13` | Sem níveis; já causou o vazamento do item 2. |

### Projeto 3 — `task-manager-api` (Python/Flask, Task Manager parcialmente organizado)

| # | Severidade | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded** | `app.py:13` (`SECRET_KEY`), `services/notification_service.py:9-10` (usuário/senha SMTP) | Segredos versionados. |
| 2 | CRITICAL | **Hash de senha exposto na API** | `models/user.py:16-25` (`to_dict` inclui `password`), usado em `routes/user_routes.py:33, 85, 129, 212` | Reproduzido: `GET /users/1` e `POST /login` devolvem o hash MD5 (`81dc9bdb…` = `"1234"`). |
| 3 | CRITICAL | **MD5 sem salt para senhas** + senha mínima de 4 caracteres | `models/user.py:27-32`, `routes/user_routes.py:64, 115` | MD5 é quebrável por rainbow tables em segundos. |
| 4 | HIGH | **Autenticação falsa e escalonamento de privilégio** | `routes/user_routes.py:210` (`'fake-jwt-token-' + id`), `routes/user_routes.py:52, 71` (cliente escolhe `role: admin`) | Token previsível e nunca verificado; qualquer um cria um admin. |
| 5 | HIGH | **Rotas "gordas": acesso a dados + regra de negócio + serialização, sem controllers** | `routes/task_routes.py:11-63, 85-154, 156-223`, `routes/report_routes.py:12-101`, `routes/user_routes.py:42-90` | A separação em pastas é só aparente; `services/` existe mas não é usado por nenhuma rota. |
| 6 | HIGH | **Sem app factory, efeitos colaterais no import, debug em `0.0.0.0`** | `app.py:9-31` (`db.create_all()` no import), `app.py:34`, `seed.py:2` (`from app import app, db`) | Impossível configurar para testes; importar o módulo já toca o banco. |
| 7 | MEDIUM | **Queries N+1** | `routes/task_routes.py:41-57`, `routes/user_routes.py:22` (`len(u.tasks)` lazy), `routes/report_routes.py:55-68`, `157-165` | 1 + 2N queries para listar tasks; 1 query por usuário e por categoria nos relatórios. |
| 8 | MEDIUM | **APIs deprecated** | `Query.get()` legado no SQLAlchemy 2.0: `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227`, `routes/user_routes.py:29, 94, 136, 155`, `routes/report_routes.py:105, 192, 213`; `datetime.utcnow()` deprecated no Python 3.12+: `models/task.py:15-16, 52`, `models/user.py:14`, `models/category.py:11`, `routes/task_routes.py:31, 72, 215, 285`, `routes/user_routes.py:172`, `routes/report_routes.py:35, 42, 45, 71, 133`, `utils/helpers.py:38`, `services/notification_service.py:35`, `seed.py:66-74` | Confirmado com `python -W default`: `LegacyAPIWarning` e `DeprecationWarning`. Substitutos: `db.session.get(Model, id)` e `datetime.now(timezone.utc)`. |
| 9 | MEDIUM | **Duplicação da regra "overdue" e da serialização** | `routes/task_routes.py:30-39, 71-80, 283-287`, `routes/user_routes.py:171-180`, `routes/report_routes.py:34-43, 132-135` (enquanto `models/task.py:50-60` já tem `is_overdue`); `routes/task_routes.py:17-28` ≈ `Task.to_dict`; regex de e-mail em `routes/user_routes.py:61, 106` e `utils/helpers.py:19-23` | A mesma regra reimplementada 6 vezes. |
| 10 | MEDIUM | **Validação frágil → 500** | `routes/task_routes.py:113` (`priority` string), `routes/report_routes.py:196-197` (`data` `None`), `routes/user_routes.py:124-125` (`active` sem validação) | Entradas comuns derrubam a rota com erro interno. |
| 11 | MEDIUM | **`except:` genérico e sem handler central** | `routes/task_routes.py:62, 137, 204, 236`, `routes/user_routes.py:130, 149`, `routes/report_routes.py:186, 207, 221`, `utils/helpers.py:46, 49, 88` | Engole qualquer erro (inclusive `KeyboardInterrupt`), esconde bugs. |
| 12 | MEDIUM | **Agregações ineficientes** | `routes/report_routes.py:15-28` (12 `COUNT` separados), `routes/task_routes.py:275-287` (carrega todas as tasks para contar atrasadas) | Deveria ser `GROUP BY`/filtro no banco. |
| 13 | LOW | **Imports não usados** | `app.py:7`, `routes/task_routes.py:7`, `routes/user_routes.py:6`, `routes/report_routes.py:7-8`, `models/task.py:3`, `utils/helpers.py:2-7` | Ruído. |
| 14 | LOW | **Código morto** | `utils/helpers.py:57-116` (`process_task_data` e constantes nunca usados), `services/notification_service.py` (nunca instanciado), `models/task.py:38-48` (`validate_*` nunca chamados) | Funcionalidade aparente que não existe. |
| 15 | LOW | **Condicionais verbosas / não idiomáticas** | `models/task.py:38-60`, `models/user.py:34-38`, `routes/task_routes.py:141, 210` (`type(x) == list`) | Legibilidade. |
| 16 | LOW | **Magic numbers + `print` como log** | `routes/task_routes.py:96-100, 113` (3, 200, 1..5), `routes/report_routes.py:45, 129` (7 dias, prioridade ≤ 2); `routes/task_routes.py:149, 153, 219, 234`, `routes/user_routes.py:83, 89, 147` | Regras sem nome; logs sem nível. |
