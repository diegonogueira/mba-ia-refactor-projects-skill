# Refatoração Arquitetural Automatizada com a Skill `refactor-arch`

Entrega do desafio **Criação de Skills — Refatoração Arquitetural Automatizada** (MBA IA). O enunciado original está preservado em [`docs/ENUNCIADO.md`](docs/ENUNCIADO.md).

A skill `refactor-arch` (Claude Code) analisa uma codebase, audita anti-patterns com severidade e `arquivo:linha`, pede confirmação e refatora o projeto para MVC, validando que a aplicação continua de pé e que todos os endpoints originais respondem.

**Resultado em uma linha:** a mesma skill (copiada sem alterações) rodou nos 3 projetos. Detectou a stack correta, encontrou 25, 21 e 20 findings (6/5/3 CRITICAL), pausou para confirmação e refatorou para MVC. As 3 APIs sobem e respondem a todas as rotas originais, o que foi validado pela skill e por um script independente comparando com o código original ([Resultados](#c-resultados)).

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

---

## B) Construção da Skill

### Estrutura

```text
.claude/skills/refactor-arch/            # idêntica nos 3 projetos (diff -r vazio)
├── SKILL.md                             # orquestrador: regras críticas + 3 fases + troubleshooting (~150 linhas)
└── references/
    ├── project-analysis.md              # Análise de projeto (Fase 1)
    ├── anti-patterns-catalog.md         # Catálogo de anti-patterns, com APIs deprecated (Fase 2)
    ├── report-template.md               # Template dos relatórios das Fases 1, 2 e 3
    ├── mvc-guidelines.md                # Guidelines de arquitetura MVC (Fase 3)
    ├── refactoring-playbook.md          # Playbook de refatoração com antes/depois (Fase 3)
    └── validation-guide.md              # Extra: baseline, boot, smoke test, comparação, troubleshooting (Fase 3)
```

| Área de conhecimento obrigatória | Arquivo | Conteúdo principal |
|---|---|---|
| Análise de projeto | `project-analysis.md` | Tabelas de detecção de linguagem (10 ecossistemas), framework e versão (manifesto + lockfile; 10+ frameworks), banco e tabelas, entry point, inventário de endpoints por framework, classificação da arquitetura (monólito, módulos planos, parcialmente em camadas, MVC, Clean) e inferência de domínio |
| Catálogo de anti-patterns | `anti-patterns-catalog.md` | 24 anti-patterns com regra de severidade, sinais de detecção (regex + checagens estruturais), falsos positivos ("Not a finding when") e transformação do playbook. Inclui a tabela de APIs deprecated (AP-18) |
| Template de relatório | `report-template.md` | Formato exato da Fase 1, do relatório da Fase 2 (Summary, Findings, Deprecated APIs, Total) e do resumo da Fase 3, com regras de contagem e ordenação |
| Guidelines de arquitetura | `mvc-guidelines.md` | Responsabilidades e proibições de cada camada, regra de dependências, layouts-alvo para Flask e Express, mapeamento para FastAPI/Django/NestJS/Spring/Rails, composition root, config, erros, **preservação de contrato** e estratégia por ponto de partida |
| Playbook de refatoração | `refactoring-playbook.md` | 18 transformações (T-01 a T-18) com código antes/depois em Python e JavaScript |

### Decisões de design

1. **SKILL.md como prompt orquestrador, conhecimento nas referências.** Segue a *progressive disclosure* do guia da Anthropic: o frontmatter fica sempre no contexto, o corpo do SKILL.md carrega quando a skill é invocada e cada fase manda ler só as referências de que precisa (a Fase 1 não carrega o playbook, por exemplo). O SKILL.md tem ~150 linhas, bem abaixo do limite recomendado de 500.
2. **Regras críticas no topo**, como recomenda o guia ("Put critical instructions at the top"): ordem das fases, Fases 1–2 somente leitura, pausa obrigatória, `arquivo:linha` verificado, preservação de contrato, validação real, ficar dentro do projeto e idioma.
3. **Frontmatter pensado para segurança:**
   - `name` em kebab-case igual ao nome da pasta; `description` diz o que a skill faz e quando usar, com frases de gatilho, sem `<` `>` e com menos de 1024 caracteres.
   - `allowed-tools` pré-aprova **só ferramentas de leitura** (`Read`, `Grep`, `Glob`, `find`, `ls`, `wc`, `grep`, `git status`, `npm audit`). Pela documentação, essa concessão vale apenas no turno da invocação, que é justamente o das Fases 1 e 2. A Fase 3 começa na resposta do usuário (`y`), quando a concessão já expirou, então nenhuma escrita é pré-aprovada.
   - Não usei `disable-model-invocation`: a skill pode ser sugerida pelo modelo, mas a pausa da Fase 2 garante que nada seja modificado sem confirmação humana.
4. **Dynamic context injection (`` ```! ``):** ao carregar, a skill injeta a lista de arquivos do projeto (sem `node_modules`, `.venv`, `.git`) e o `git status`. Isso economiza chamadas na Fase 1 e permite avisar sobre alterações não commitadas antes da Fase 3 (o que aconteceu no projeto 2). Os comandos terminam com `|| true`, porque uma falha na injeção abortaria a skill inteira.
5. **Pausa portável:** a Fase 2 termina com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e **encerra o turno**, sem depender de uma ferramenta de pergunta. Assim funciona no modo interativo (`claude "/refactor-arch"`) e no headless (`claude -p` + `--resume <sessão> "y"`), que usei para gerar logs reproduzíveis.
6. **Validação baseada em baseline:** antes de alterar qualquer arquivo, a Fase 3 sobe a aplicação **original**, roda um smoke test com todos os endpoints do inventário da Fase 1 e guarda o resultado fora do projeto. Depois da refatoração, roda o mesmo teste e compara status e shape das respostas. Por isso a linha "All endpoints respond correctly" é medida, não declarada.
7. **Preservação de contrato com exceções explícitas:** rotas, métodos, nomes de campos, envelopes, porta e comando de start não mudam. Há 7 exceções permitidas, todas de segurança ou integridade (remover segredos/hashes das respostas, desabilitar endpoints de SQL arbitrário, 500 → 400 em entrada inválida, etc.), e cada uma precisa aparecer em "Contract Changes". Mudanças que exigem decisão de produto, como tornar autenticação obrigatória, vão para "Remaining Items".
8. **Honestidade no resultado:** o template só permite ✓ para checagens realmente executadas. Nos 3 projetos a skill marcou ✗ em "Zero CRITICAL/HIGH remaining", porque manteve de propósito a ausência de autenticação para não quebrar o contrato, e explicou o motivo.
9. **Relatório em Markdown renderizável:** banners em blocos `text` e findings como listas com rótulos em negrito. A saída fica legível no terminal e pode ser salva direto em `reports/` sem edição.

### Anti-patterns do catálogo e por quê

| Severidade | Anti-patterns | Por que estão no catálogo |
|---|---|---|
| CRITICAL | AP-01 Credenciais hardcoded · AP-02 SQL injection · AP-03 God Class/God module · AP-04 Exposição de dados sensíveis (respostas e logs) · AP-05 Armazenamento inseguro de senhas · AP-06 Endpoints destrutivos/debug sem proteção e autenticação quebrada | São os exemplos da definição de CRITICAL do enunciado e apareceram na análise manual dos 3 projetos: SQL concatenado, `/admin/query`, `badCrypto`, MD5, hash devolvido pela API, cartão no log |
| HIGH | AP-07 Regra de negócio em rotas/controllers · AP-08 Acoplamento sem DI / sem composition root · AP-09 Estado global mutável · AP-10 Configuração de runtime insegura · AP-11 Escritas não atômicas · AP-12 Integridade referencial quebrada | Violações de MVC/SOLID citadas na definição de HIGH, mais dois problemas de dados que encontrei na prática (checkout sem transação, exclusão que deixa órfãos) |
| MEDIUM | AP-13 N+1 · AP-14 Validação ausente · AP-15 Exceções engolidas / sem handler central · AP-16 Código duplicado · AP-17 Callback hell · **AP-18 APIs e dependências deprecated** · AP-19 Uso inadequado de middlewares | Os exemplos de MEDIUM do enunciado, mais callback hell (típico de Node legado) e a detecção de APIs obsoletas exigida pelo desafio |
| LOW | AP-20 Magic numbers · AP-21 Nomes ruins · AP-22 Código morto / imports não usados · AP-23 `print`/`console.log` como log · AP-24 Condicionais verbosas | Os exemplos de LOW do enunciado e ruídos recorrentes nos 3 projetos |

O **AP-18** traz uma tabela de APIs obsoletas com o substituto moderno: `datetime.utcnow()` → `datetime.now(timezone.utc)`, `Model.query.get()` → `db.session.get()`, removidos do Flask 2.3/3.0, `new Buffer()`, `url.parse()`, remoções do Express 5, `body-parser`, entre outros. A detecção sempre é cruzada com as versões do manifesto e aceita como evidência a saída do gerenciador de pacotes (`npm audit`, avisos `deprecated` do lockfile). O catálogo também tem **regras de escalonamento**: problema explorável remotamente sem autenticação é no mínimo HIGH; entrada comum que gera 500 é no mínimo MEDIUM; API já removida na versão instalada é HIGH.

### Como garanti que a skill é agnóstica de tecnologia

- **Sinais descritos por responsabilidade, não por nome de arquivo:** "rota que executa SQL", "handler com cálculo de regra", "query dentro de loop". Cada sinal vem com padrões para Python e JavaScript.
- **Heurísticas multi-ecossistema** na Fase 1 (Python, Node/TS, Go, Java/Kotlin, Ruby, PHP, .NET, Elixir, Rust) e um mapeamento de MVC para frameworks que não são Flask/Express (FastAPI, Django, NestJS, Spring, Rails/Laravel).
- **Exemplos neutros:** o playbook usa domínios genéricos (orders, invoices, subscriptions, articles) em vez de copiar o código dos projetos-alvo. Na primeira versão os exemplos se pareciam demais com os projetos e foram generalizados antes da primeira execução.
- **Estratégia por ponto de partida** (`mvc-guidelines.md` §10): monólito, módulos planos, parcialmente em camadas ou já MVC, cada um com um plano diferente. O projeto 3 comprova isso: models do SQLAlchemy reaproveitados, `routes/` convertidas em `views/` + `controllers/`, código morto removido.
- **A prova:** a mesma pasta, copiada sem nenhuma alteração (`diff -r` vazio), rodou nos 3 projetos, em 2 stacks e 2 níveis de organização.

### Desafios encontrados e como resolvi

| # | Desafio | Solução |
|---|---|---|
| 1 | **Iteração 1:** na primeira execução no projeto 1, a Fase 2 imprimiu o relatório inteiro dentro de um bloco de código (ilegível ao salvar) e, na Fase 3, o agente começou a ler `scripts/` na raiz do repositório, fora do projeto | Interrompi a execução, restaurei o projeto e lancei a v1.1.0 (commit `79f68e4`): template em Markdown renderizável, regra "Stay inside the project" e fallback para quando não há ferramenta de task list. Depois reexecutei as 3 fases do zero. |
| 2 | Tensão entre **corrigir segurança** e manter "os endpoints originais respondendo" (ex.: `/admin/query` executa SQL arbitrário) | Seção de preservação de contrato com exceções permitidas. O endpoint continua registrado, mas desabilitado por padrão (403), só com flag + token, e restrito a um único `SELECT` numa conexão somente leitura. |
| 3 | Garantir **linhas exatas** nos findings | Regra de citar apenas linhas lidas com número (`cat -n`/`grep -n`) e ordenação determinística. Conferi com um script as 406 localizações dos 3 relatórios contra o código original: 0 fora do intervalo. Também fiz checagens por amostragem do conteúdo das linhas. |
| 4 | Validação instável (servidor Flask com reloader sobrevivendo ao `kill`, porta ocupada) | `validation-guide.md` manda subir o servidor com `setsid` e matar o process group, e ainda traz uma tabela de troubleshooting. |
| 5 | `npm` recente bloqueia scripts de instalação: o binário nativo do `sqlite3` não é compilado (`Could not locate the bindings file`) | Diagnóstico e solução (`npm install-scripts approve` + `npm rebuild`) no troubleshooting. A skill aplicou a correção sozinha no projeto 2 (`allowScripts` no `package.json`). |
| 6 | Saída poluída por avisos de conectores MCP do meu ambiente na execução headless | Execuções com `--strict-mcp-config`, que desliga servidores MCP. É um ajuste de ambiente, não da skill. |
| 7 | Projetos 1 e 3 usam a mesma porta (5000) | As Fases 1–2 dos 3 projetos rodaram em paralelo (somente leitura), mas a Fase 3 do projeto 3 só começou depois do fim da Fase 3 do projeto 1. |
| 8 | Risco de *overfitting* da skill aos 3 projetos | Exemplos genéricos no playbook e sinais por responsabilidade (ver seção anterior). |

---

## C) Resultados

Todas as execuções foram feitas com o Claude Code 2.1.273 (modelo `claude-opus-5[1m]`), usando a skill v1.1.0. Os logs completos de cada projeto (saída das Fases 1 e 3, confirmação e linha do tempo de ferramentas) estão em [`docs/execution-logs/`](docs/execution-logs/).

### Resumo dos relatórios de auditoria

| Projeto | Stack detectada | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python + Flask 3.1.1 | 6 | 7 | 7 | 5 | **25** | [`reports/audit-project-1.md`](reports/audit-project-1.md) |
| 2 — ecommerce-api-legacy | JavaScript (Node.js) + Express 4.22.1 | 5 | 8 | 4 | 4 | **21** | [`reports/audit-project-2.md`](reports/audit-project-2.md) |
| 3 — task-manager-api | Python + Flask 3.0.0 | 3 | 6 | 6 | 5 | **20** | [`reports/audit-project-3.md`](reports/audit-project-3.md) |

**Cobertura da análise manual:** a skill encontrou **todos** os problemas da seção A (17/17, 18/18 e 16/16), às vezes agrupados num único finding. Também encontrou problemas que eu não tinha listado:

- **Projeto 1:** exclusão de produto que apaga histórico de pedidos (AP-12), e-mails em log (LGPD) e ausência de sessão/token no login.
- **Projeto 2:** `card` numérico derruba o processo inteiro (DoS com uma requisição); checkout reaproveita contas existentes sem verificar a senha.
- **Projeto 3:** CVEs nas versões fixadas (`flask-cors` 4.0.0, `requests` 2.31.0…), dependências declaradas e nunca importadas, e CRUD de categorias escondido no blueprint de relatórios.

**APIs deprecated:**

- **Projeto 1:** nenhuma no código (`None detected`). As versões vulneráveis de `flask`/`flask-cors` foram detectadas na re-auditoria da Fase 3 com `pip-audit` e atualizadas.
- **Projeto 2:** dependências `deprecated`/vulneráveis no lockfile.
- **Projeto 3:** `datetime.utcnow()` e `Query.get()`, com o substituto moderno.

### Custo e tempo das execuções

| Projeto | Fases 1 + 2 | Fase 3 | Ferramentas (Fases 1–2 / 3) |
|---|---|---|---|
| 1 | 5,7 min · US$ 1,88 | 15,3 min · US$ 7,26 | 6 / 53 |
| 2 | 5,4 min · US$ 1,85 | 12,0 min · US$ 5,55 | 11 / 65 |
| 3 | 7,0 min · US$ 2,57 | 14,7 min · US$ 8,43 | 17 / 70 |

Nas Fases 1–2 houve **zero** chamadas de escrita nos 3 projetos, conferido na linha do tempo dos logs.

### Antes × depois

#### Projeto 1 — code-smells-project (4 arquivos / 780 linhas → 39 arquivos / 1159 linhas)

```text
ANTES                                         DEPOIS
code-smells-project/                          code-smells-project/
├── app.py          # config + rotas +        ├── app.py                 # entry point (python app.py)
│                   # SQL admin + boot        ├── .env.example
├── controllers.py  # HTTP + validação +      ├── requirements.txt       # flask 3.1.3, flask-cors 6.0.5
│                   # "notificações"          └── src/
├── models.py       # SQL concatenado +           ├── app.py             # composition root: create_app()
│                   # regras de 4 domínios        ├── config/            # settings.py, logging_config.py
├── database.py     # conexão global +            ├── models/            # database, seed, produto, usuario, pedido,
│                   # schema + seed               │                      # relatorio, sistema, admin
└── requirements.txt                              ├── services/          # pedido_service, notification_service
                                                  ├── controllers/       # produto, usuario, pedido, relatorio, sistema, admin
                                                  ├── views/             # *_routes.py (blueprints) + serializers.py
                                                  ├── middlewares/       # error_handler.py, admin_guard.py
                                                  └── utils/             # errors.py, validators.py
```

#### Projeto 2 — ecommerce-api-legacy (3 arquivos / 180 linhas → 27 arquivos / 584 linhas)

```text
ANTES                                         DEPOIS
ecommerce-api-legacy/                         ecommerce-api-legacy/
├── package.json                              ├── package.json          # sqlite3 ^6.0.1, allowScripts
├── api.http                                  ├── .env.example
└── src/                                      └── src/
    ├── app.js         # instancia a God          ├── app.js            # entry point: settings → db → createApp → listen
    │                  # Class e dá listen        ├── createApp.js      # composition root
    ├── AppManager.js  # conexão, schema,         ├── config/           # settings.js
    │                  # seed, rotas, SQL,        ├── models/           # database (promises + transaction), schema,
    │                  # pagamento, relatório     │                     # user, course, enrollment, payment, auditLog, financialReport
    └── utils.js       # segredos, cache          ├── services/         # checkout, paymentGateway, report, user
                       # global, badCrypto        ├── controllers/      # checkout, report, user
                                                  ├── views/            # routes.js, serializers.js
                                                  ├── middlewares/      # errorHandler, asyncHandler, adminGuard
                                                  └── utils/            # errors, validators, password (scrypt), logger
```

#### Projeto 3 — task-manager-api (15 arquivos / 1158 linhas → 37 arquivos / 1338 linhas)

```text
ANTES                                         DEPOIS
task-manager-api/                             task-manager-api/
├── app.py        # app global, config        ├── app.py                # entry point (python app.py)
│                 # hardcoded, create_all     ├── seed.py               # CLI usando create_app()
├── database.py                               ├── requirements.txt      # flask 3.1.3, flask-cors 6.0.5, itsdangerous
├── seed.py       # importa o app global      ├── .env.example
├── models/       # task, user (MD5),         └── src/
│                 # category                      ├── app.py            # composition root
├── routes/       # rotas "gordas": validação     ├── config/           # settings.py, logging_config.py
│                 # + queries + regras            ├── models/           # database (mixin), task_model, user_model,
├── services/     # notification_service          │                     # category_model, seed
│                 # (nunca usado)                 ├── services/         # report_service, auth_service (token assinado)
└── utils/        # helpers.py (nunca usado)      ├── controllers/      # task, user, category, report, health, validators, lookups
                                                  ├── views/            # task/user/category/report/health routes + serializers
                                                  ├── middlewares/      # error_handler.py
                                                  └── utils/            # errors, dates (utc_now), calculations
```

### Checklist de validação

Cada item marcado traz, depois do travessão, a evidência que conferi.

#### Projeto 1 — code-smells-project

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — Python
- [x] Framework detectado corretamente — Flask 3.1.1 (requirements.txt)
- [x] Domínio da aplicação descrito corretamente — E-commerce API (produtos, usuarios, pedidos, itens_pedido)
- [x] Número de arquivos analisados condiz com a realidade — 4 arquivos (~780 linhas; real: 780)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 156 localizações conferidas, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados — 25
- [x] Detecção de APIs deprecated incluída (se aplicável) — seção presente; nenhuma API deprecated no código
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — src/{models,views,controllers} + config, services, middlewares
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.py + .env.example
- [x] Models criados para abstrair dados — models por domínio (produto, usuario, pedido, relatorio, sistema, admin) + database/seed, todos com SQL parametrizado
- [x] Views/Routes separadas para visualização ou roteamento — 6 blueprints + serializers
- [x] Controllers concentram o fluxo da aplicação — 6 controllers
- [x] Error handling centralizado — src/middlewares/error_handler.py
- [x] Entry point claro — app.py → src/app.py:create_app()
- [x] Aplicação inicia sem erros — python app.py, porta 5000
- [x] Endpoints originais respondem corretamente — 19/19 rotas; 31/36 checks idênticos + 5 mudanças de contrato documentadas
```

#### Projeto 2 — ecommerce-api-legacy

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — JavaScript (Node.js)
- [x] Framework detectado corretamente — Express 4.22.1 (resolvido no lockfile; ^4.18.2 no package.json)
- [x] Domínio da aplicação descrito corretamente — LMS API com checkout (users, courses, enrollments, payments, audit_logs)
- [x] Número de arquivos analisados condiz com a realidade — 3 arquivos (~180 linhas; real: 180)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 73 localizações conferidas, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados — 21
- [x] Detecção de APIs deprecated incluída (se aplicável) — dependências deprecated/vulneráveis (sqlite3@5 → tar@6, inflight, glob@7…)
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — src/{models,views,controllers} + config, services, middlewares
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.js + .env.example
- [x] Models criados para abstrair dados — 8 módulos em src/models
- [x] Views/Routes separadas para visualização ou roteamento — src/views/routes.js + serializers.js
- [x] Controllers concentram o fluxo da aplicação — 3 controllers
- [x] Error handling centralizado — src/middlewares/errorHandler.js + asyncHandler.js
- [x] Entry point claro — npm start → src/app.js → src/createApp.js
- [x] Aplicação inicia sem erros — npm ci limpo + node src/app.js, porta 3000
- [x] Endpoints originais respondem corretamente — 3/3 rotas; 7/8 checks idênticos + 1 mudança documentada (integridade no DELETE)
```

#### Projeto 3 — task-manager-api

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — Python
- [x] Framework detectado corretamente — Flask 3.0.0 (+ Flask-SQLAlchemy 3.1.1)
- [x] Domínio da aplicação descrito corretamente — Task Manager API (tasks, users, categories, reports)
- [x] Número de arquivos analisados condiz com a realidade — 15 arquivos (~1158 linhas, 3 __init__.py vazios; real: 1158)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 177 localizações conferidas, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados — 20
- [x] Detecção de APIs deprecated incluída (se aplicável) — datetime.utcnow() e Query.get(), com substitutos
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — routes/ → views/ + controllers/; models, services, config, middlewares
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.py + .env.example
- [x] Models criados para abstrair dados — Task/User/Category com consultas encapsuladas (GROUP BY, joinedload)
- [x] Views/Routes separadas para visualização ou roteamento — 5 blueprints + serializers
- [x] Controllers concentram o fluxo da aplicação — 5 controllers + validators
- [x] Error handling centralizado — src/middlewares/error_handler.py
- [x] Entry point claro — app.py e seed.py usam src/app.py:create_app()
- [x] Aplicação inicia sem erros — python seed.py && python app.py, porta 5000
- [x] Endpoints originais respondem corretamente — 22/22 rotas; 40/44 checks idênticos + 4 mudanças documentadas (remoção do hash de senha)
```

### Evidências: aplicações rodando após a refatoração

Além da validação feita pela própria skill, **validei de forma independente** com [`scripts/validate.sh`](scripts/validate.sh). O script copia cada projeto refatorado para um diretório temporário, instala as dependências do zero, sobe a API, roda [`scripts/smoke_test.py`](scripts/smoke_test.py) (36, 8 e 44 requisições, cobrindo todas as rotas, casos de erro e payloads de ataque) e compara com a execução do **código original** gravada antes da refatoração ([`docs/validation/baseline-p*.json`](docs/validation/)).

| Projeto | Boot | Checks idênticos ao original | Diferenças (todas previstas em "Contract Changes") | Log do servidor |
|---|---|---|---|---|
| 1 | ✅ `python app.py` | 31/36 | `/health` sem `secret_key`/`debug`/`db_path`; `/usuarios/1` sem `senha`; busca com `' OR '1'='1` → lista vazia; `/admin/query` e `/admin/reset-db` → 403 | [`server-p1.log`](docs/validation/server-p1.log) |
| 2 | ✅ `node src/app.js` (após `npm ci`) | 7/8 | relatório após `DELETE /api/users/1` não traz mais aluno "Unknown" com pagamento órfão | [`server-p2.log`](docs/validation/server-p2.log) |
| 3 | ✅ `python seed.py && python app.py` | 40/44 | `password` removido de `GET/POST/PUT /users` e de `POST /login` | [`server-p3.log`](docs/validation/server-p3.log) |

Tabelas completas: [`comparison-p1.md`](docs/validation/comparison-p1.md), [`comparison-p2.md`](docs/validation/comparison-p2.md), [`comparison-p3.md`](docs/validation/comparison-p3.md). Trecho da saída de `scripts/validate.sh all`:

```text
=== Projeto 1: code-smells-project (Python/Flask) ===
  ✓ servidor respondeu na porta 5000
| POST | `/login` | 200 | 200 | igual |
| GET | `/produtos/busca?q=%27%20OR%20%271%27%3D%271` | 200 | 200 | DIFERENTE: shape (dados: lista vazia) |
| POST | `/admin/query` | 200 | 403 | DIFERENTE: status 200 → 403; shape (-dados, -sucesso, +erro) |
31/36 checks idênticos (status + shape); 5 diferenças para revisar.
  ✓ log do servidor sem tracebacks (docs/validation/server-p1.log)
=== Projeto 2: ecommerce-api-legacy (Node.js/Express) ===
  ✓ servidor respondeu na porta 3000
| POST | `/api/checkout` | 200 | 200 | igual |
| GET | `/api/admin/financial-report` | 200 | 200 | DIFERENTE: shape ([].students: lista vazia) |
7/8 checks idênticos (status + shape); 1 diferenças para revisar.
  ✓ log do servidor sem tracebacks (docs/validation/server-p2.log)
=== Projeto 3: task-manager-api (Python/Flask) ===
Seed concluído com sucesso!
  ✓ servidor respondeu na porta 5000
| POST | `/login` | 200 | 200 | DIFERENTE: shape (-user.password) |
| GET | `/reports/summary` | 200 | 200 | igual |
40/44 checks idênticos (status + shape); 4 diferenças para revisar.
  ✓ log do servidor sem tracebacks (docs/validation/server-p3.log)
```

Log do servidor do projeto 2 após a refatoração (cartão mascarado e nenhuma chave de gateway):

```text
[...] WARN PAYMENT_GATEWAY_KEY não definida; usando gateway de pagamento simulado
[...] WARN ADMIN_TOKEN não definido; rotas administrativas estão sem autenticação
[...] INFO LMS API rodando na porta 3000
[...] INFO Pagamento de 497 no cartão ****4444: PAID
[...] INFO Checkout concluído: matrícula 2 no curso 2
```

Durante a Fase 3, a própria skill fez validações extras, registradas nos logs de execução. Alguns exemplos:

- **Projeto 1:** 20 pedidos concorrentes para estoque 8 resultaram em exatamente 8 criados e estoque final 0; `pip-audit` sem vulnerabilidades.
- **Projeto 2:** falha simulada no insert de pagamento → rollback; `npm audit` com 0 vulnerabilidades (eram 12); relatório financeiro com 1 query (antes 1 + C + 2·E).
- **Projeto 3:** contagem de queries medida (`/tasks` passou de 1 + 2N para 1 query); hash MD5 legado migrado para scrypt no primeiro login.

### Observações sobre o comportamento em stacks diferentes

- **Monólito Python (projeto 1):** a skill criou a estrutura completa e dividiu por domínio (produto, usuário, pedido, relatório, sistema, admin). Manteve SQL puro, agora parametrizado, porque as guidelines proíbem trocar a tecnologia de acesso a dados. Também introduziu conexão por requisição (`flask.g`) e transações com `BEGIN IMMEDIATE`.
- **God Class Node.js (projeto 2):** as transformações foram outras. Callback hell virou `async/await` com um wrapper de Promise para o `sqlite3`, entrou uma fila de transações (conexão única), e erros assíncronos passaram a ser propagados ao middleware via `asyncHandler`. As respostas de erro continuaram em **texto puro**, como no original, e não viraram JSON, o que mostra que a skill respeitou o contrato de cada stack. Ela também lidou sozinha com o bloqueio de scripts do npm moderno.
- **Flask parcialmente organizado (projeto 3):** a skill **não recriou do zero**. Reaproveitou os models SQLAlchemy (agora com consultas encapsuladas e `GROUP BY`), transformou `routes/` em `views/` + `controllers/`, separou categorias do blueprint de relatórios, removeu `services/` e `utils/` que nunca eram usados e trocou APIs deprecated.
- **Decisões consistentes nos 3:** a autenticação obrigatória **não** foi adicionada, porque mudaria o contrato. Ficou como item pendente com ✗ explícito na validação. Endpoints perigosos ganharam proteção proporcional ao risco: SQL arbitrário desabilitado por padrão no projeto 1 e guard opcional via `ADMIN_TOKEN` no projeto 2.
- **Variações entre execuções** (o agente não é determinístico): o default de `HOST` ficou `0.0.0.0` no projeto 1, igual ao original, e `127.0.0.1` no projeto 3, com a mudança documentada em "Contract Changes". Em ambos é configurável por variável de ambiente.

---

## D) Como Executar

### Pré-requisitos

| Ferramenta | Versão usada | Observação |
|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/overview) | 2.1.273 | `curl -fsSL https://claude.ai/install.sh \| bash`, depois `claude` para fazer login |
| Python | 3.14.7 (≥ 3.10) | Projetos 1 e 3 (`uv` é opcional, mas acelera a instalação) |
| Node.js + npm | 26.8.1 / 12.0.2 (Node ≥ 20.17) | Projeto 2 (`sqlite3@6` exige Node ≥ 20.17) |
| git, curl | — | Validação |

### Executar a skill (ordem sugerida: projeto 1 → 2 → 3)

Modo interativo, conforme o enunciado:

```bash
cd code-smells-project && claude "/refactor-arch"      # Fases 1 e 2 → responda "y" para a Fase 3
cd ../ecommerce-api-legacy && claude "/refactor-arch"
cd ../task-manager-api && claude "/refactor-arch"
```

Modo headless, como usei para gerar os logs:

```bash
cd code-smells-project
claude -p "/refactor-arch" --output-format json > fase12.json                 # Fases 1-2 (somente leitura) e pausa
python3 -c "import json; print(json.load(open('fase12.json'))['result'])"     # lê o relatório
SESSION=$(python3 -c "import json; print(json.load(open('fase12.json'))['session_id'])")
claude -p "y" --resume "$SESSION" --permission-mode acceptEdits --allowedTools "Bash"   # confirma e executa a Fase 3
```

> Em modo `-p` não há como aprovar permissões interativamente, então a Fase 3 (que edita arquivos, instala dependências e sobe servidores) precisa de `--permission-mode`/`--allowedTools`. Nas minhas execuções usei o modo `auto` configurado no meu `settings.json`, sem nenhuma permissão negada (`permission_denials: []` em todas as sessões).

> O código deste repositório **já está refatorado**. Para reexecutar a skill sobre o código original, crie um worktree do commit base e copie a skill:
>
> ```bash
> git worktree add ../original 6d1ce62
> for p in code-smells-project ecommerce-api-legacy task-manager-api; do
>   cp -r "$p/.claude" "../original/$p/"
> done
> cd ../original/code-smells-project && claude "/refactor-arch"
> ```

### Validar que a refatoração funcionou

Validação automática (instala dependências em diretório temporário, sobe cada API e compara com o original):

```bash
scripts/validate.sh all        # ou: scripts/validate.sh 1 | 2 | 3
```

Validação manual:

```bash
# Projeto 1
cd code-smells-project && pip install -r requirements.txt && python app.py
curl localhost:5000/health
curl "localhost:5000/produtos/busca?q=Mouse"
curl -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"admin@loja.com","senha":"admin123"}'

# Projeto 2
cd ecommerce-api-legacy && npm install && npm start
curl -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
     -d '{"usr":"Ana","eml":"ana@teste.com","pwd":"segredo","c_id":2,"card":"4111222233334444"}'
curl localhost:3000/api/admin/financial-report          # ou use api.http

# Projeto 3
cd task-manager-api && pip install -r requirements.txt && python seed.py && python app.py
curl localhost:5000/tasks
curl localhost:5000/reports/summary
curl -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"joao@email.com","password":"1234"}'
```

Variáveis de ambiente de cada projeto (todas opcionais para rodar localmente) estão no `.env.example` e no README de cada projeto.

### Estrutura do repositório

```text
mba-ia-refactor-projects-skill/
├── README.md                        # este documento
├── code-smells-project/             # Projeto 1 refatorado + .claude/skills/refactor-arch/
├── ecommerce-api-legacy/            # Projeto 2 refatorado + .claude/skills/refactor-arch/ (cópia idêntica)
├── task-manager-api/                # Projeto 3 refatorado + .claude/skills/refactor-arch/ (cópia idêntica)
├── reports/
│   ├── audit-project-1.md           # saída da Fase 2 (verbatim)
│   ├── audit-project-2.md
│   └── audit-project-3.md
├── docs/
│   ├── ENUNCIADO.md                 # enunciado original do desafio
│   ├── execution-logs/              # saída das Fases 1 e 3 + linha do tempo de ferramentas, por projeto
│   └── validation/                  # baseline do código original, resultados pós-refatoração, comparações e logs
└── scripts/
    ├── smoke_test.py                # exercita todos os endpoints de um projeto
    ├── compare_results.py           # compara baseline × refatorado (status + shape)
    └── validate.sh                  # validação ponta a ponta dos 3 projetos
```
