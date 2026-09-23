# Refatoração Arquitetural Automatizada com a Skill `refactor-arch`

Entrega do desafio **Criação de Skills — Refatoração Arquitetural Automatizada** (MBA IA). O enunciado original está preservado em [`docs/ENUNCIADO.md`](docs/ENUNCIADO.md).

A skill `refactor-arch` (Claude Code) analisa uma codebase, audita anti-patterns com severidade e `arquivo:linha`, pede confirmação e refatora o projeto para MVC, validando que a aplicação continua de pé e que todos os endpoints originais respondem.

**Resultado em uma linha:** a mesma skill (copiada sem alterações nos 3 projetos) detectou a stack correta, encontrou 26, 21 e 21 findings (6/5/3 CRITICAL), pausou para confirmação e refatorou tudo para MVC. As 3 APIs sobem e respondem a todas as rotas originais — validado pela skill e por dois scripts independentes: um compara request a request com o código original, o outro prova com as apps no ar que os achados de autorização foram mesmo fechados ([Resultados](#c-resultados)).

> **Iteração pós-avaliação (skill v1.4.0).** Um feedback apontou que o relatório do projeto 3 classificava escalação de privilégio como HIGH, mas a Fase 3 tinha deixado `POST /users` aceitando `role: admin`. Investiguei, achei o padrão por trás disso e corrigi a skill e os 3 projetos — o relato está em [Iteração pós-avaliação](#iteração-pós-avaliação-feedback-da-banca).
>
> **Segunda iteração (skill v1.5.0/v1.5.1).** Um novo feedback mostrou que o `audit-project-1.md` registrava "cancelar o pedido não devolve o estoque", mas a refatoração só tinha mudado o código de camada — o `notificacao_service` seguia apenas logando `"Devolver estoque."`. O playbook ganhou a regra de fechar o comportamento descrito no **Impact** (e não só mover o código) e a skill foi rodada de novo no projeto 1: cancelar agora devolve o estoque, uma única vez, e todos os endpoints originais continuam respondendo como antes — ver [Segunda iteração](#segunda-iteração-o-impact-que-não-fechava-skill-v150-e-v151).

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
| 13 | MEDIUM | **Tratamento de erro genérico que vaza exceção** e nenhum handler central | `controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292` (16 blocos `except Exception as e` que devolvem `str(e)` com status 500) | Mensagens internas vão para o cliente; código repetido em cada handler. |
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
| 11 | MEDIUM | **Callback hell** (até 6 callbacks aninhados: curso → usuário → insert usuário → matrícula → pagamento → auditoria) | `src/AppManager.js:37-77` | Fluxo ilegível, tratamento de erro duplicado a cada nível, `self = this` (linha 26). |
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
| 2 | CRITICAL | **Hash de senha exposto na API** | `models/user.py:16-25` (`to_dict` inclui `password`), usado em `routes/user_routes.py:33, 85, 129, 209` | Reproduzido: `GET /users/1` e `POST /login` devolvem o hash MD5 (`81dc9bdb…` = `"1234"`). |
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

Versão final: **v1.5.1** (o histórico das iterações está em [Desafios](#desafios-encontrados-e-como-resolvi) e em [Iteração pós-avaliação](#iteração-pós-avaliação-feedback-da-banca)).

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
| Playbook de refatoração | `refactoring-playbook.md` | 19 transformações (T-01 a T-19) com código antes/depois em Python e JavaScript, precedidas da "Rule zero": o finding só fecha quando o Impact deixa de acontecer |

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
7. **Preservação de contrato com exceções explícitas:** rotas, métodos, nomes de campos, envelopes, porta e comando de start não mudam. Há 10 exceções permitidas, todas de segurança ou integridade (remover segredos/hashes das respostas, fechar endpoints destrutivos por padrão, 500 → 400 em entrada inválida, tirar segredos de log e seed, barrar escalação de privilégio, implementar a regra que o código anuncia e não executa, etc.), e cada uma precisa aparecer em "Contract Changes". Mudanças que exigem decisão de produto, como tornar autenticação obrigatória, vão para "Remaining Items".
8. **Honestidade no resultado:** o template só permite ✓ para checagens realmente executadas. Nos 3 projetos a skill marcou ✗ em "Zero CRITICAL/HIGH remaining", porque manteve de propósito a ausência de autenticação para não quebrar o contrato, e explicou o motivo.
9. **Auditoria de dependências obrigatória na Fase 2:** além dos greps de APIs obsoletas no código, a skill roda um audit somente leitura por ecossistema (`npm audit --package-lock-only`, campo `vulnerabilities` da API do PyPI) e precisa registrar no relatório se o registry estava inacessível, em vez de assumir que está tudo bem (veio da iteração 2).
10. **Relatório em Markdown renderizável:** banners em blocos `text` e findings como listas com rótulos em negrito. A saída fica legível no terminal e pode ser salva direto em `reports/` sem edição.

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
| 1 | **Iteração 1 (v1.0.0 → v1.1.0):** na primeira execução no projeto 1, a Fase 2 imprimiu o relatório inteiro dentro de um bloco de código (ilegível ao salvar) e, na Fase 3, o agente começou a ler `scripts/` na raiz do repositório, fora do projeto | Interrompi a execução, restaurei o projeto e lancei a v1.1.0 (commit `79f68e4`): template em Markdown renderizável, regra "Stay inside the project" e fallback para quando não há ferramenta de task list. Depois reexecutei as 3 fases do zero. |
| 2 | **Iteração 2 (v1.1.0 → v1.2.0):** rodei uma revisão independente da entrega (um agente com contexto limpo conferindo tudo contra o enunciado). Ela apontou que a detecção de dependências vulneráveis na Fase 2 era não determinística (o projeto 1 saiu com "None detected" e o 3 consultou o PyPI por conta própria), que os controllers importavam serializers da view contrariando a regra de dependências das próprias guidelines, que o default de `HOST` saiu diferente em cada projeto e que ainda havia literais dos projetos-alvo nos exemplos das referências | Lancei a v1.2.0 (commit `5ca9a20`): audit de dependências obrigatório com método definido por ecossistema, regra de escopo mais dura (nada fora do projeto, rede só para registries), guideline explícita de que o controller escolhe/renderiza a view, `HOST=127.0.0.1` como padrão, idioma dos arquivos gerados e exemplos generalizados. Restaurei os 3 projetos para o código original e **reexecutei as 3 fases nos 3**, para que o que está commitado venha da versão final da skill. |
| 3 | Tensão entre **corrigir segurança** e manter "os endpoints originais respondendo" (ex.: `/admin/query` executa SQL arbitrário) | Seção de preservação de contrato com exceções permitidas. O endpoint continua registrado, mas desabilitado por padrão (403), só com flag + token, e restrito a um único `SELECT` numa conexão somente leitura. |
| 4 | Garantir **linhas exatas** nos findings | Regra de citar apenas linhas lidas com número (`cat -n`/`grep -n`) e ordenação determinística. Conferi com [`scripts/check_report_locations.py`](scripts/check_report_locations.py) as 403 localizações dos 3 relatórios contra o código original: 0 fora do intervalo. Também fiz checagens por amostragem do conteúdo das linhas. |
| 5 | Validação instável (servidor Flask com reloader sobrevivendo ao `kill`, porta ocupada) | `validation-guide.md` manda subir o servidor com `setsid` e matar o process group, e ainda traz uma tabela de troubleshooting. |
| 6 | `npm` recente bloqueia scripts de instalação: o binário nativo do `sqlite3` não é compilado (`Could not locate the bindings file`) | Diagnóstico e solução (`npm install-scripts approve` + `npm rebuild`) no troubleshooting. A skill aplicou a correção sozinha no projeto 2 (`allowScripts` no `package.json`). |
| 7 | Saída poluída por avisos de conectores MCP do meu ambiente na execução headless | Execuções com `--strict-mcp-config`, que desliga servidores MCP. É um ajuste de ambiente, não da skill. |
| 8 | Projetos 1 e 3 usam a mesma porta (5000), e a Fase 3 sobe a aplicação para validar | As Fases 1–2 dos 3 projetos rodaram em paralelo (somente leitura); nas Fases 3, projetos 1 e 2 rodaram juntos (portas 5000 e 3000) e o projeto 3 só começou depois do fim do projeto 1. |
| 9 | Risco de *overfitting* da skill aos 3 projetos | Exemplos genéricos no playbook e sinais por responsabilidade (ver seção anterior). |
| 11 | **Iteração 3 (v1.2.0 → v1.4.0), depois do feedback da banca:** a Fase 3 escondia correções possíveis atrás de "precisa de autenticação" — `POST /users` continuava aceitando `role: admin` no projeto 3, e o mesmo padrão aparecia em mais 7 pontos nos 3 projetos | Varredura finding-a-finding dos 68 achados, skill v1.3.0/v1.4.0 (exceção 9 para escalação de privilégio, exceção 8 para segredo em log/seed, guarda fechada por padrão, headers no contrato, fechamento finding a finding com `Status`), reexecução das 3 fases nos 3 projetos e `scripts/security_probes.sh` com 29 provas. Detalhes em [Iteração pós-avaliação](#iteração-pós-avaliação-feedback-da-banca). |
| 12 | **Iteração 4 (v1.4.0 → v1.5.1), segundo feedback da banca:** o relatório do projeto 1 dizia que cancelar não devolve o estoque, mas a Fase 3 só moveu o `print` para `notificacao_service` — o Impact continuava acontecendo | Playbook com "Rule zero" (fechar o Impact, não só a camada) e T-19 (comportamento anunciado e não executado), sinal novo no AP-07, Recommendation obrigada a cobrir o Impact, `Fixed` só quando o cenário do Impact não se reproduz. A primeira reexecução (v1.5.0) fechou listagens do domínio com 403; a v1.5.1 restringiu a exceção 2 ao que é administrativo por natureza e a reexecução final manteve o contrato. Provas de estoque em `security_probes.sh`. Detalhes em [Segunda iteração](#segunda-iteração-o-impact-que-não-fechava-skill-v150). |
| 10 | O limite de uso da conta (`You've hit your session limit`) interrompeu a Fase 3 dos projetos 1 e 2 no meio | Retomei a **mesma sessão** depois da renovação (`claude -p "...continue de onde parou" --resume <sessão>`) e a skill seguiu do ponto em que estava. Os logs e as métricas registram a interrupção e as duas invocações. |


---

## C) Resultados

Os relatórios `audit-project-{1,2,3}.md`, os números e as comparações desta seção vêm das execuções da **skill v1.2.0** (Claude Code 2.1.273, modelo `claude-opus-5[1m]`) sobre o código original (commit `6d1ce62`). Depois disso, o código foi refinado em reexecuções da skill sobre o próprio código refatorado, descritas em [Iteração pós-avaliação](#iteração-pós-avaliação-feedback-da-banca) e na [Segunda iteração](#segunda-iteração-o-impact-que-não-fechava-skill-v150-e-v151): projetos 2 e 3 com a v1.4.0, projeto 1 com a v1.5.1 (Claude Code 2.1.280, modelo `claude-opus-5-5[1m]`). Os logs completos de cada projeto — saída das Fases 1 e 3, confirmação e linha do tempo de todas as chamadas de ferramenta — estão em [`docs/execution-logs/`](docs/execution-logs/).

### Resumo dos relatórios de auditoria

| Projeto | Stack detectada | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python + Flask 3.1.1 | 6 | 8 | 7 | 5 | **26** | [`reports/audit-project-1.md`](reports/audit-project-1.md) |
| 2 — ecommerce-api-legacy | JavaScript (Node.js) + Express 4.22.1 | 5 | 7 | 5 | 4 | **21** | [`reports/audit-project-2.md`](reports/audit-project-2.md) |
| 3 — task-manager-api | Python + Flask 3.0.0 | 3 | 6 | 7 | 5 | **21** | [`reports/audit-project-3.md`](reports/audit-project-3.md) |

Conferências que fiz nos relatórios:

- **Localizações válidas:** `scripts/check_report_locations.py` conferiu as 157, 72 e 174 localizações citadas nas linhas `File:` contra o código original — **0 fora do intervalo**, 0 arquivos inexistentes. Também conferi por amostragem o conteúdo das linhas (SQL concatenado, `SECRET_KEY`, `to_dict` com senha, `badCrypto`, `utcnow`, `except:`).
- **Contagens:** o `Summary` e o `Total` de cada relatório batem com a quantidade de títulos `### [SEVERIDADE]` (validado por script na geração dos arquivos).
- **Ordenação:** severidade CRITICAL → HIGH → MEDIUM → LOW correta nos 3. A ordenação secundária (arquivo, depois linha) tem **duas inversões** no relatório 1: `Inconsistent Response Envelopes` (`app.py:64`) aparece depois de `Generic Exception Handling` (`app.py:77`), e `Magic Numbers and Strings` (`app.py:36`) depois de `print Logging` (`app.py:56`).

**Cobertura da análise manual:** a skill encontrou **todos** os problemas que eu havia documentado na seção A (17/17 no projeto 1, 18/18 no projeto 2 e 16/16 no projeto 3), às vezes agrupados num único finding — por exemplo, o CORS liberado entrou em `Insecure Runtime Configuration` e as 12 queries de `COUNT` entraram em `N+1 Queries and Per-Row Aggregation`. Achados que ela trouxe **além** da minha análise:

- **Projeto 1:** `DELETE /produtos/<id>` apaga o histórico de pedidos (integridade referencial), e-mails em log (LGPD), login sem token/sessão e envelopes de erro inconsistentes entre rotas.
- **Projeto 2:** `card` numérico derruba o processo inteiro (DoS com uma requisição, porque a exceção acontece dentro do callback do sqlite3); checkout reaproveita conta existente sem conferir a senha.
- **Projeto 3:** CVEs nas versões fixadas, três dependências declaradas e nunca importadas, e o CRUD de categorias escondido no blueprint de relatórios.

**APIs deprecated e dependências (AP-18):** com a auditoria obrigatória da v1.2.0, os 3 relatórios trazem a seção preenchida.

| Projeto | No código | Nas dependências |
|---|---|---|
| 1 | nenhuma API da tabela de obsoletas (verificado com grep para as versões detectadas) | `flask==3.1.1` (CVE-2026-27205) e `flask-cors==5.0.1` (CVE-2024-6839/6844/6866), via API do PyPI |
| 2 | — | `npm audit --package-lock-only`: 12 vulnerabilidades (1 critical, 7 high) em `path-to-regexp`, `qs`, `body-parser`, `tar`, `node-gyp`…, mais 9 pacotes marcados `deprecated` no lockfile |
| 3 | `datetime.utcnow()` em 21 localizações (23 ocorrências) → `datetime.now(timezone.utc)`; `Query.get()` legado em 16 pontos → `db.session.get()` | `flask==3.0.0`, `flask-cors==4.0.0` e 3 pacotes não importados (`marshmallow`, `requests`, `python-dotenv`), todos com CVE |

### Custo e tempo das execuções

| Projeto | Fases 1 + 2 (somente leitura) | Fase 3 | Ferramentas (Fases 1-2 / Fase 3) |
|---|---|---|---|
| 1 | 3,8 min · US$ 1,41 | 14,5 min · US$ 7,54 | 10 / 60 |
| 2 | 5,2 min · US$ 1,67 | 13,3 min · US$ 7,07 | 12 / 70 |
| 3 | 5,4 min · US$ 1,76 | 16,6 min · US$ 10,64 | 10 / 62 |

Valores tirados do campo `total_cost_usd` e das durações dos eventos `result` de cada sessão; estão repetidos na tabela de cada log em `docs/execution-logs/`. Nas Fases 1–2 houve **zero** chamadas de escrita nos 3 projetos e nenhuma permissão negada (`permission_denials: []` em todas as sessões), o que confirma que a auditoria é somente leitura.

> A Fase 3 dos projetos 1 e 2 foi interrompida no meio pelo limite de uso da minha conta (`You've hit your session limit`). Retomei **a mesma sessão** depois da renovação e a skill continuou do ponto em que parou; as métricas acima somam as duas invocações. Os logs registram a interrupção e a mensagem de retomada.

### Antes × depois

#### Projeto 1 — code-smells-project (4 arquivos / 780 linhas → 35 arquivos / 1239 linhas)

```text
ANTES                                        DEPOIS
code-smells-project/                         code-smells-project/
├── app.py          # config + rotas +       ├── app.py                 # entry point (python app.py)
│                   # SQL admin + boot       ├── .env.example
├── controllers.py  # HTTP + validação +     ├── requirements.txt       # flask 3.1.3, flask-cors 6.0.5
│                   # "notificações"         └── src/
├── models.py       # SQL concatenado +          ├── app.py             # composition root: create_app()
│                   # regras de 4 domínios       ├── config/            # settings.py (env vars)
├── database.py     # conexão global +           ├── models/            # database (conexão por request + transação),
│                   # schema + seed              │                      # produto, usuario, pedido, relatorio, sistema
└── requirements.txt                             ├── services/          # pedido_service, notificacao_service
                                                 ├── controllers/      # produto, usuario, pedido, relatorio, sistema
                                                 │                      # + validators.py
                                                 ├── views/             # *_routes.py (blueprints) + serializers.py + converters.py
                                                 ├── middlewares/       # error_handler.py, admin_guard.py
                                                 └── utils/             # errors.py
```

#### Projeto 2 — ecommerce-api-legacy (3 arquivos / 180 linhas → 28 arquivos / 666 linhas)

```text
ANTES                                        DEPOIS
ecommerce-api-legacy/                        ecommerce-api-legacy/
├── package.json                             ├── package.json          # express ^4.22.3, sqlite3 ^6.0.1, allowScripts
├── api.http                                 ├── .env.example
└── src/                                     └── src/
    ├── app.js         # instancia a God         ├── app.js            # entry point: settings → banco → listen
    │                  # Class e dá listen       ├── createApp.js      # composition root
    ├── AppManager.js  # conexão, schema,        ├── config/           # settings.js
    │                  # seed, rotas, SQL,       ├── models/           # database (promises + fila + transaction),
    │                  # pagamento, relatório    │                     # schema (FKs, UNIQUE), user, course,
    └── utils.js       # segredos, cache         │                     # enrollment, payment, auditLog, financialReport
                       # global, badCrypto       ├── services/         # checkout, user, paymentGateway
                                                 ├── controllers/      # checkout, report, user
                                                 ├── views/            # routes.js, presenters.js
                                                 ├── middlewares/      # errorHandler, asyncHandler, adminGuard
                                                 └── utils/            # errors, constants, logger, password, validators
```

#### Projeto 3 — task-manager-api (15 arquivos / 1158 linhas → 39 arquivos / 1536 linhas)

```text
ANTES                                        DEPOIS
task-manager-api/                            task-manager-api/
├── app.py        # app global, config       ├── app.py                # entry point (python app.py)
│                 # hardcoded, create_all    ├── seed.py               # usa create_app()
├── database.py   # no import                ├── requirements.txt      # flask 3.1.3, flask-cors 6.0.5, python-dotenv
├── seed.py       # importa o app global     ├── .env.example
├── models/       # task, user (MD5),        └── src/
│                 # category                    ├── app.py            # composition root
├── routes/       # rotas "gordas":              ├── config/           # settings.py (env vars)
│                 # validação + queries         ├── models/           # database (mixin), task, user, category, seed
│                 # + regras                    ├── services/         # auth_service (token assinado), report_service
├── services/     # notification_service         ├── controllers/      # task, user, category, report, health
│                 # (nunca usado)               │                      # + validators/ por domínio
└── utils/        # helpers.py (nunca usado)     ├── views/            # *_routes.py (blueprints, categorias separadas
                                                 │                      # dos relatórios) + serializers.py
                                                 ├── middlewares/      # error_handler.py
                                                 └── utils/            # errors, validators, datetime_utils, math_utils
```

### Checklist de validação

Cada item traz, depois do travessão, a evidência que conferi.

#### Projeto 1 — code-smells-project

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — Python
- [x] Framework detectado corretamente — Flask 3.1.1 (pin do requirements.txt)
- [x] Domínio da aplicação descrito corretamente — E-commerce API (produtos, usuarios, pedidos, itens_pedido)
- [x] Número de arquivos analisados condiz com a realidade — 4 arquivos, ~780 linhas (real: 780)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 157 localizações conferidas por script, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW) — com 1 inversão na ordem secundária (arquivo/linha)
- [x] Mínimo de 5 findings identificados — 26 (6 CRITICAL)
- [x] Detecção de APIs deprecated incluída (se aplicável) — nenhuma API obsoleta no código; 2 dependências vulneráveis (CVEs) detectadas via PyPI
- [x] Skill pausa e pede confirmação antes da Fase 3 — turno encerrado com a pergunta; 0 escritas nas Fases 1-2

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — src/{models,views,controllers} + config, services, middlewares, utils
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.py + .env.example (as senhas de exemplo do seed continuam no código, com hash e desligáveis por SEED_DATABASE=false)
- [x] Models criados para abstrair dados — 5 models de domínio (produto, usuario, pedido, relatorio, sistema) + database com conexão por requisição e transações; SQL só neles
- [x] Views/Routes separadas para visualização ou roteamento — 5 blueprints + serializers com allowlist de campos
- [x] Controllers concentram o fluxo da aplicação — 5 controllers + validators
- [x] Error handling centralizado — src/middlewares/error_handler.py (AppError/HTTPException/Exception → JSON)
- [x] Entry point claro — app.py → src/app.py:create_app()
- [x] Aplicação inicia sem erros — `python app.py`, porta 5000, debug off, log sem traceback
- [x] Endpoints originais respondem corretamente — 19/19 rotas registradas; 19/36 checks idênticos + 17 diferenças esperadas (11 só ganharam `"sucesso": false` no erro, 2 sem campos sensíveis, 2 admin → 403 por padrão, 1 busca imune a SQL injection, 1 login de demonstração sem senha fixa no seed — todas listadas em `docs/validation/expected-differences.json`). Os endpoints `/admin/*` continuam registrados e respondendo: 403 enquanto desabilitados e 200 com `ADMIN_ENDPOINTS_ENABLED=true` + `X-Admin-Token`
```

#### Projeto 2 — ecommerce-api-legacy

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — JavaScript (Node.js)
- [x] Framework detectado corretamente — Express 4.22.1 (versão resolvida no lockfile; ^4.18.2 no package.json)
- [x] Domínio da aplicação descrito corretamente — LMS API com checkout (users, courses, enrollments, payments, audit_logs)
- [x] Número de arquivos analisados condiz com a realidade — 3 arquivos, ~180 linhas (real: 180)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 72 localizações conferidas por script, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW) — ordem primária e secundária corretas
- [x] Mínimo de 5 findings identificados — 21 (5 CRITICAL)
- [x] Detecção de APIs deprecated incluída (se aplicável) — `npm audit --package-lock-only` (12 vulnerabilidades) + pacotes `deprecated` do lockfile, com substituto indicado
- [x] Skill pausa e pede confirmação antes da Fase 3 — turno encerrado com a pergunta e aviso de working tree suja; 0 escritas nas Fases 1-2

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — src/{models,views,controllers} + config, services, middlewares, utils
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.js + .env.example; nenhum segredo restante (grep)
- [x] Models criados para abstrair dados — 9 módulos em src/models (SQL só neles), com schema, FKs e transações
- [x] Views/Routes separadas para visualização ou roteamento — src/views/routes.js + presenters.js
- [x] Controllers concentram o fluxo da aplicação — 3 controllers finos (validação → service → presenter)
- [x] Error handling centralizado — src/middlewares/errorHandler.js + asyncHandler.js (erros em texto, como no original)
- [x] Entry point claro — `npm start` → src/app.js → src/createApp.js
- [x] Aplicação inicia sem erros — `npm ci` limpo (build nativo do sqlite3 ok) + `node src/app.js`, porta 3000
- [x] Endpoints originais respondem corretamente — 3/3 rotas; 5/8 checks idênticos + 3 diferenças esperadas (as 2 rotas administrativas passaram a ser fechadas por padrão — com `ADMIN_ENDPOINTS_ENABLED` + `ADMIN_TOKEN` respondem como o original)
```

#### Projeto 3 — task-manager-api

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente — Python
- [x] Framework detectado corretamente — Flask 3.0.0 (+ Flask-SQLAlchemy 3.1.1)
- [x] Domínio da aplicação descrito corretamente — Task Manager API (tasks, users, categories)
- [x] Número de arquivos analisados condiz com a realidade — 15 arquivos (3 __init__.py vazios), ~1158 linhas (real: 1158)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos — 174 localizações conferidas por script, 0 inválidas
- [x] Findings ordenados por severidade (CRITICAL → LOW) — ordem primária e secundária corretas
- [x] Mínimo de 5 findings identificados — 21 (3 CRITICAL, 6 HIGH)
- [x] Detecção de APIs deprecated incluída (se aplicável) — `datetime.utcnow()` (21 localizações) e `Query.get()` (16 pontos) com substituto moderno, + 5 pins com CVE
- [x] Skill pausa e pede confirmação antes da Fase 3 — turno encerrado com a pergunta; 0 escritas nas Fases 1-2

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC — routes/ → views/ + controllers/; models, services, config, middlewares, utils
- [x] Configuração extraída para módulo de config (sem hardcoded) — src/config/settings.py + .env.example; credenciais SMTP eliminadas junto com o serviço morto
- [x] Models criados para abstrair dados — Task/User/Category com consultas encapsuladas (GROUP BY, joinedload) e mixin de persistência
- [x] Views/Routes separadas para visualização ou roteamento — 5 blueprints + serializers (sem hash de senha)
- [x] Controllers concentram o fluxo da aplicação — 5 controllers (ações de 5 a 15 linhas) + validators por domínio
- [x] Error handling centralizado — src/middlewares/error_handler.py (nenhuma resposta HTML restante)
- [x] Entry point claro — app.py e seed.py usam src/app.py:create_app()
- [x] Aplicação inicia sem erros — `python seed.py && python app.py`, porta 5000, sem DeprecationWarning
- [x] Endpoints originais respondem corretamente — 22/22 rotas; 39/44 checks idênticos + 5 diferenças esperadas (hash de senha fora das respostas, login de demonstração sem senha fixa no seed, `DELETE /users/<id>` atrás da guarda administrativa)
```

### Evidências: aplicações rodando após a refatoração

Além da validação feita pela própria skill, **validei de forma independente** com [`scripts/validate.sh`](scripts/validate.sh): ele copia cada projeto refatorado para um diretório temporário, instala as dependências do zero, sobe a API, roda [`scripts/smoke_test.py`](scripts/smoke_test.py) (36, 8 e 44 requisições cobrindo todas as rotas, casos de erro e payloads de ataque) e compara com a execução do **código original**, gravada antes da refatoração em [`docs/validation/baseline-p*.json`](docs/validation/). Diferenças só passam se estiverem declaradas em [`expected-differences.json`](docs/validation/expected-differences.json); qualquer outra derruba o script com código de saída 1.

```text
$ scripts/validate.sh all
=== Projeto 1: code-smells-project (Python/Flask) ===
  ✓ servidor respondeu na porta 5000
  19/36 checks idênticos (status + shape); 17 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
  ✓ log do servidor sem tracebacks
=== Projeto 2: ecommerce-api-legacy (Node.js/Express) ===
  ✓ servidor respondeu na porta 3000
  5/8 checks idênticos (status + shape); 3 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
  ✓ log do servidor sem tracebacks
=== Projeto 3: task-manager-api (Python/Flask) ===
  Seed concluído com sucesso!
    3 usuários
    4 categorias
    10 tasks
  ✓ servidor respondeu na porta 5000
  39/44 checks idênticos (status + shape); 5 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
  ✓ log do servidor sem tracebacks

✓ Todos os projetos validados
```

Tabelas completas request a request: [`comparison-p1.md`](docs/validation/comparison-p1.md), [`comparison-p2.md`](docs/validation/comparison-p2.md), [`comparison-p3.md`](docs/validation/comparison-p3.md). Logs dos servidores refatorados: [`server-p1.log`](docs/validation/server-p1.log), [`server-p2.log`](docs/validation/server-p2.log), [`server-p3.log`](docs/validation/server-p3.log).

Log do projeto 2 depois da refatoração — cartão mascarado, nenhuma chave de gateway e aviso de que a proteção admin está desligada:

```text
2026-09-17T18:07:29.249Z [WARN] ADMIN_TOKEN não definido: as rotas administrativas continuam públicas.
2026-09-17T18:07:29.256Z [INFO] LMS API rodando em http://127.0.0.1:3000
2026-09-17T18:07:29.706Z [INFO] Processando pagamento de 497 no cartão ****4444
```

Durante a Fase 3 a própria skill fez validações extras, registradas nos logs de execução. Alguns exemplos:

- **Projeto 1:** 10 pedidos concorrentes para estoque 1 → exatamente 1 criado e estoque final 0; falha forçada por trigger no meio da transação → nada gravado; login com `' OR 1=1 --` → 401 (antes: 200); `/admin/query` com escrita ou múltiplos comandos → 400; CORS comparado com o original.
- **Projeto 2:** requisição que derrubava o processo (`card` numérico) → 400 e servidor de pé; 20 checkouts simultâneos com o mesmo e-mail criam 1 usuário; bateria repetida com `sqlite3` 5.1.7 e 6.0.1 com resultado idêntico; `npm audit` 0 vulnerabilidades (antes: 12).
- **Projeto 3:** zero `DeprecationWarning`/`LegacyAPIWarning` (baseline: 32); nenhuma resposta 500 ou HTML no smoke test (baseline: 7 e 9); hash MD5 legado autentica e é migrado para scrypt.

### Observações sobre o comportamento em stacks diferentes

- **Monólito Python (projeto 1):** criou a estrutura completa e dividiu por domínio. Manteve SQL puro — agora parametrizado —, porque as guidelines proíbem trocar a tecnologia de acesso a dados, e introduziu conexão por requisição (`flask.g`) e transações com `BEGIN IMMEDIATE`.
- **God Class Node.js (projeto 2):** transformações bem diferentes. Callback hell virou `async/await` com um wrapper de Promise para o `sqlite3` e uma fila de transações (conexão única), erros assíncronos passaram a chegar ao middleware via `asyncHandler`, e as respostas de erro continuaram em **texto puro**, como no original, em vez de virar JSON. Ela também resolveu sozinha o bloqueio de scripts de instalação do npm 12 (`allowScripts`) e validou o app com as duas versões do `sqlite3`.
- **Flask parcialmente organizado (projeto 3):** não recriou do zero. Reaproveitou os models SQLAlchemy (agora com consultas encapsuladas, `GROUP BY` e `joinedload`), transformou `routes/` em `views/` + `controllers/`, tirou o CRUD de categorias do módulo de relatórios, removeu `utils/helpers.py` e o `NotificationService` que ninguém usava e trocou as APIs deprecated.
- **Decisões consistentes nos 3:** autenticação obrigatória **não** foi adicionada, porque mudaria o contrato de rotas hoje públicas — em todos os projetos isso ficou como item pendente e com ✗ explícito na validação. Endpoints perigosos ganharam proteção proporcional ao risco: SQL arbitrário desabilitado por padrão no projeto 1 e guard opt-in via `ADMIN_TOKEN` no projeto 2.
- **Convenções que ficaram diferentes entre os projetos:** comentários de código em inglês no projeto 2 e em português nos projetos 1 e 3; injeção de dependência por fábricas (projetos 2 e 3) contra controllers como funções de módulo com singletons e `flask.g` (projeto 1) — o projeto 1 é o menos testável dos três; e `.env` carregado automaticamente só no projeto 3 (que manteve o `python-dotenv`), o que está corretamente descrito em cada `.env.example`. As guidelines aceitam as três variações, mas quem for manter os três projetos junto provavelmente vai querer uniformizar.
- **Limite do meu gate independente:** `scripts/compare_results.py` compara status HTTP e estrutura da resposta (chaves e tipos), não os valores. Uma regressão de valor (um total calculado errado, por exemplo) não seria pega por ele — quem cobriu isso foi a própria Fase 3, que comparou valores derivados (relatórios, estoque, contagens) com o baseline.
- **Variação entre execuções:** no projeto 1 a skill padronizou o envelope de erro adicionando `"sucesso": false` onde faltava (mudança aditiva, declarada em "Contract Changes"), enquanto nos outros dois preservou os formatos como estavam. É uma leitura mais permissiva da regra "não mudar envelopes de resposta" das guidelines: nenhum cliente quebra, mas é o tipo de decisão que eu revisaria antes de subir.

### Ajustes manuais depois da execução da skill

Para manter a rastreabilidade: **o código versionado dos 3 projetos é a saída da Fase 3 da skill**, sem retoques. Os projetos 2 e 3 vêm da reexecução com a v1.4.0 e o projeto 1 da reexecução com a v1.5.1. Quando uma execução não serviu (a v1.5.0 no projeto 1), eu restaurei o código anterior e corrigi a skill, sem editar o código à mão. A única exceção é este ajuste, feito por mim depois da revisão independente:

- `code-smells-project/requirements.txt` e `task-manager-api/requirements.txt` passaram a declarar `werkzeug==3.1.8` (usado em `generate_password_hash`/`check_password_hash` e nos handlers de erro) e `itsdangerous==2.2.0` (token assinado do projeto 3). Os dois vinham só como dependência transitiva do Flask, o que é frágil num upgrade — e é exatamente o tipo de problema que os relatórios da skill cobram do código legado.

### Iteração pós-avaliação (feedback da banca)

**O apontamento.** O relatório do projeto 3 classificava escalação de privilégio como HIGH, mas a Fase 3 tinha deixado `POST /users` lendo `role` do corpo (`user_validator.py:54`) — qualquer um se cadastrava como `admin`. Procede: a skill tinha jogado o item inteiro em "Remaining Items" como decisão de produto, porque a recomendação mencionava autenticação.

**A causa raiz.** Rodei uma varredura finding-a-finding (agente com contexto limpo) conferindo **cada um dos 68 findings** dos 3 relatórios contra o código refatorado, subindo as aplicações. O caso do `role` não era isolado: sempre que a correção tocava em *quem pode fazer o quê*, a Fase 3 parava e rotulava como decisão de produto, mesmo quando havia conserto possível sem autenticação. Oito lacunas, todas corrigíveis sem mexer no contrato de requisições legítimas:

| # | Projeto | Lacuna | Prova antes da correção |
|---|---|---|---|
| 1 | task-manager-api | `POST /users` aceitava `role` | `201 {"role":"admin"}` |
| 2 | task-manager-api | `PUT /users/<id>` deixava anônimo promover/desativar qualquer conta | `maria` → `admin`, `active:false` |
| 3 | ecommerce-api-legacy | guarda administrativa *opt-in*: sem `ADMIN_TOKEN`, relatório financeiro e `DELETE /api/users/:id` ficavam públicos (finding CRITICAL) | ambos → 200 sem token |
| 4 | task-manager-api | hash de senha vazava nos parâmetros do erro de banco | `IntegrityError ... [parameters: (...scrypt...)]` |
| 5 | code-smells-project | `/admin/query` continuava executando SQL do cliente (a recomendação era remover) e devolvia hashes | `SELECT email,senha FROM usuarios` → 200 |
| 6 | code-smells-project | seed criava `admin@loja.com`/`admin123` por padrão | `POST /login` → 200 |
| 7 | code-smells-project | 405 perdeu o header `Allow` — regressão introduzida pela refatoração | `DELETE /health` → 405 sem `Allow` |
| 8 | task-manager-api | `SQLAlchemy` sem versão fixada | `requirements.txt` |

**A correção na skill (v1.3.0 → v1.4.0).** Mudei as regras, não os projetos:

- `mvc-guidelines.md` §9 ganhou a exceção 9 — campo de privilégio (`role`, `is_admin`, `permissions`, `active`) vindo de cliente anônimo **tem** de parar de conceder privilégio, no create e no update; é correção de segurança, não decisão de produto — e a regra **"não esconda um problema corrigível atrás de um maior"**: "isso precisa de autenticação" só cobre a parte que realmente precisa.
- Guarda de endpoint destrutivo/administrativo tem de ser **fechada por padrão**; guarda opt-in não fecha um CRITICAL, e o padrão vale igual nos três projetos (era inconsistente: o projeto 1 negava por padrão, o 2 deixava aberto).
- Headers que o framework enviava (`Allow` no 405, CORS) entraram na lista do que o contrato preserva.
- Proibido logar parâmetros de banco e semear conta privilegiada com senha conhecida; `/admin/query` não pode ler coluna de credencial.
- A Fase 3 passou a fechar **finding a finding**: cada achado da Fase 2 aparece na tabela com `Status` (`Fixed` / `Partially fixed` / `Not fixed`), relendo a própria recomendação, e roda 4 provas de fechamento antes de declarar corrigido.

**A reexecução.** Rodei as 3 fases de novo nos 3 projetos (agora sobre o código já refatorado — a Fase 1 detecta "MVC em camadas" e audita o que sobrou). Achados e resultado:

| Projeto | Findings na reauditoria | Fechados | Relatório | Log |
|---|---|---|---|---|
| 1 — code-smells-project | 9 (0 CRITICAL, 1 HIGH) | 7 `Fixed`, 1 `Partially fixed`, 1 `Not fixed` | [`audit-project-1-rerun.md`](reports/audit-project-1-rerun.md) | [log](docs/execution-logs/rerun-v140-project-1-code-smells-project.md) |
| 2 — ecommerce-api-legacy | 9 (1 CRITICAL, 1 HIGH) | 5 `Fixed`, 2 `Partially fixed`, 2 `Not fixed` | [`audit-project-2-rerun.md`](reports/audit-project-2-rerun.md) | [log](docs/execution-logs/rerun-v140-project-2-ecommerce-api-legacy.md) |
| 3 — task-manager-api | 8 + 7 (duas rodadas) | escalação fechada na 1ª, log/seed/dependência na 2ª | [v1.3.0](reports/audit-project-3-rerun-v130.md) · [v1.4.0](reports/audit-project-3-rerun.md) | [log v1.3.0](docs/execution-logs/rerun-v130-project-3-task-manager-api.md) · [log v1.4.0](docs/execution-logs/rerun-v140-project-3-task-manager-api.md) |

O único CRITICAL/HIGH que segue aberto é o mesmo de antes e continua legítimo: **não existe autenticação nas rotas** do projeto 3 (e das rotas de gestão do projeto 1) — adicionar login obrigatório transformaria requisições hoje bem-sucedidas em 401. A parte corrigível desse mesmo finding foi fechada, e a skill agora é obrigada a dizer explicitamente o que fechou e o que não fechou.

**Provas, não declarações.** Criei [`scripts/security_probes.sh`](scripts/security_probes.sh): sobe cada aplicação e verifica na prática o que os relatórios afirmam — 29 provas, todas passando (38 depois da segunda iteração). A prova do vazamento no log força um `IntegrityError` de verdade (o e-mail duplicado é barrado pelo validador antes do banco, então a versão ingênua não detectaria nada) e foi conferida com controle negativo: reativando `hide_parameters=False` numa cópia, ela falha como esperado.

```text
=== Projeto 1: code-smells-project ===
  PASS  endpoint de SQL arbitrário fechado por padrão (HTTP 403)
  PASS  405 preserva o header Allow
  PASS  consulta que cita coluna de credencial é recusada (HTTP 400)
  PASS  SELECT * em usuarios não devolve hash
=== Projeto 2: ecommerce-api-legacy ===
  PASS  relatório financeiro fechado por padrão (HTTP 403)
  PASS  relatório financeiro com token (HTTP 200)
  PASS  checkout duplicado é recusado (HTTP 400)
=== Projeto 3: task-manager-api ===
  PASS  auto-cadastro como admin é recusado (HTTP 403)
  PASS  promoção de conta alheia é recusada (HTTP 403)
  PASS  auto-cadastro comum continua funcionando (HTTP 201)
  PASS  CORS não reflete origem desconhecida
  PASS  log de erro não expõe parâmetros do banco (IntegrityError forçado)

✓ Todas as provas de segurança passaram
```

**O gate também aprendeu.** Durante a iteração ele pegou duas coisas: a mudança de 409 → 400 no e-mail duplicado (efeito da senha mínima 8, ajustei o harness e regravei o baseline) e — pior — descobri que uma entrada "esperada" engolia *qualquer* diferença naquele check, mascarando o login do projeto 3 virando 401. Agora a troca de status precisa ser declarada explicitamente (`"status": "200->401"`), senão é regressão.

**Mudanças de contrato desta iteração** (as visíveis pelo smoke test estão em `docs/validation/expected-differences.json`, com o motivo): rotas administrativas fechadas por padrão nos 3 projetos (403 sem configuração, idêntico ao original com flag + token); login de demonstração passa a depender de `SEED_PASSWORD` (ou da senha sorteada e registrada no primeiro boot), porque o seed não tem mais senha no código; checkout duplicado recusado no projeto 2; `tags` acima do limite recusadas no projeto 3. **Uma mudança não aparece no gate porque o smoke test não manda `Origin`:** o CORS deixou de refletir qualquer origem — o padrão passou a ser `http://127.0.0.1:5000` (projeto 1) e `http://localhost:3000,http://127.0.0.1:3000` (projeto 3), configurável por `CORS_ORIGINS` (`CORS_ORIGINS=*` reproduz o comportamento original). As provas de segurança cobrem esse caso.

### Segunda iteração: o Impact que não fechava (skill v1.5.0 e v1.5.1)

**O apontamento.** O `audit-project-1.md` registra, no HIGH de lógica no controller (AP-07), que cancelar um pedido não devolve o estoque. No código refatorado, `pedido_model.atualizar_status` só trocava o status e `notificacao_service` apenas registrava `"Pedido %s cancelado. Devolver estoque."`. Procede — reproduzi com a app no ar antes de mexer em qualquer coisa:

```text
  PASS  pedido baixa o estoque (47)
  PASS  cancelamento responde como antes (HTTP 200)
  FAIL  cancelar devolve o estoque — esperado 50, obtido 47
```

**A causa raiz.** A Recommendation daquele finding falava em *onde* pôr o código ("fluxo do pedido e notificações para `services/`"), não no comportamento que o Impact descrevia. A Fase 3 cumpriu a Recommendation ao pé da letra e a v1.4.0 marcava `Fixed` com base nela. Ou seja: a skill fechava findings pela **camada**, não pela **consequência**.

**A correção na skill (v1.4.0 → v1.5.0):**

- `refactoring-playbook.md` abre com a **"Rule zero — close the Impact, not just the layer"**: para cada finding, listar as consequências do Impact e mapear cada uma para a mudança que a remove; transformações estruturais (T-03, T-11, T-13, T-16) resolvem o desenho, e o comportamento precisa de mudança própria. Mover para `services/` com o comportamento ainda faltando é `Partially fixed`.
- Nova **T-19 — Implement the behavior the Impact says is missing**, com antes/depois em Python e Node (exemplo neutro: reserva cancelada que libera assentos): ação compensatória na **mesma transação** da troca de estado, **idempotente** (compare-and-set no status anterior), notificação só depois do commit e estado compensado tratado como terminal.
- A T-16 lembra que trocar `print` por logger não muda o que a mensagem afirma.
- `anti-patterns-catalog.md` (AP-07): sinal de **comportamento anunciado e não executado** (log/comentário "devolver", "refund", "release", `TODO` sem o `UPDATE` correspondente), válido mesmo em código já em MVC.
- `report-template.md`: a Recommendation precisa cobrir **cada consequência** do Impact; uma linha só é `Fixed` quando o Impact não se reproduz.
- `mvc-guidelines.md` §9: exceção 10 — implementar a regra que o código já anuncia é correção de integridade, não decisão de produto; e "mover código não é corrigir".
- `SKILL.md` 3.5: relê o Impact (não só a Recommendation) e ganha uma 5ª prova de fechamento — reproduzir na app rodando o cenário de cada Impact de comportamento, lendo os dados antes e depois e repetindo a requisição.

**Primeira reexecução (v1.5.0) — descartada.** A Fase 2 encontrou o problema sozinha e com a recomendação certa, e a Fase 3 implementou a devolução de estoque. Mas, revendo o resultado contra o enunciado, a skill tinha ido além: leu a exceção 2 das guidelines ("reports with other people's personal or financial data") de forma ampla, criou um esquema de token no login e passou a responder **403** a chamadas anônimas em `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `DELETE /produtos/<id>` e em mais 2 rotas. Isso contraria "os endpoints originais continuam respondendo", e o feedback não pedia nada disso. O relatório e o log ficaram registrados ([relatório v1.5.0](reports/audit-project-1-rerun-v150.md), [log v1.5.0](docs/execution-logs/rerun-v150-project-1-code-smells-project.md)).

**Ajuste (v1.5.0 → v1.5.1).** Corrigi a regra, não o código. A exceção 2 de `mvc-guidelines.md` §9 agora separa dois casos:
- **Administrativo por natureza — fechado por padrão:** SQL livre, reset, debug, rotas com prefixo `/admin`, exclusões em massa e exclusão de contas de usuário.
- **CRUD e listagens do domínio — continuam públicos como no original:** a falta de autenticação neles vai para "Remaining Items", e a skill não pode criar um esquema de autenticação novo só para fechá-los.

Os projetos 2 e 3 já seguiam essa linha, então não mudam. Restaurei o código do projeto 1 para a saída da v1.4.0 e rodei as 3 fases de novo.

**Reexecução válida (v1.5.1).** A Fase 2 apontou `[HIGH] Business Logic — cancelamento anuncia devolução de estoque que não acontece`, com a recomendação de transação, estados finais, compare-and-set e devolução exatamente uma vez (T-19). Para o AP-06, ela mesma explicou que fechar rotas do domínio seria quebra de contrato. A Fase 3 implementou em `src/models/pedido_model.py` (`atualizar_status`):
- `BEGIN IMMEDIATE` e leitura do status atual;
- `cancelado` e `entregue` como estados finais (sair deles → 400);
- repetir o status atual → 200, sem efeito;
- `UPDATE ... WHERE status = <anterior>` e devolução das quantidades de `itens_pedido` na mesma transação.

O `pedido_service` só notifica quando o status muda de fato.

| Findings na reauditoria | Resultado | Relatório | Log |
|---|---|---|---|
| 5 (2 CRITICAL, 1 HIGH, 1 MEDIUM, 1 LOW) | 4 `Fixed`, 1 `Not fixed` (AP-06: autenticação obrigatória nas rotas do domínio, bloqueada pelo contrato) | [`audit-project-1-rerun-v151.md`](reports/audit-project-1-rerun-v151.md) | [log](docs/execution-logs/rerun-v151-project-1-code-smells-project.md) |

Além do estoque, a reauditoria achou e fechou três outros problemas:
- **Bypass no `/admin/query`:** `SELECT 1,2,3,4,5,6 UNION ALL SELECT * FROM usuarios` renomeava as colunas, escapava do filtro por nome e devolvia o hash. Agora o `set_authorizer` do SQLite devolve `NULL` para colunas de credencial, qualquer que seja o alias.
- **Inteiros acima de 2^63−1:** davam 500; agora respondem 400 no corpo e 404 na URL.
- **Origem CORS padrão:** estava presa à porta 5000; agora é derivada de `HOST`/`PORT`.

**Provas.** `scripts/security_probes.sh` ganhou as provas do Impact, que falhavam antes e passam agora, e duas provas de que as listagens continuam públicas:

```text
  PASS  listagem de usuários continua respondendo (contrato original) (HTTP 200)
  PASS  relatório de vendas continua respondendo (contrato original) (HTTP 200)
  PASS  pedido baixa o estoque (47)
  PASS  cancelamento responde como antes (HTTP 200)
  PASS  cancelar devolve o estoque (50)
  PASS  cancelar de novo não devolve em dobro (50)
  PASS  reabrir pedido cancelado é recusado (HTTP 400)
  PASS  reabrir pedido cancelado não mexe no estoque (50)
  PASS  consulta composta que renomeia colunas não devolve hash
```

**Mudanças de contrato desta iteração:**
- `PUT /pedidos/<id>/status`: cancelar devolve o estoque, e sair de `cancelado` ou `entregue` responde 400.
- Inteiros fora da faixa de 64 bits: 500 → 400/404.

O gate `validate.sh` do projeto 1 volta a ter o mesmo resultado de antes desta iteração: 19/36 checks idênticos e 17 diferenças esperadas, com 0 diferenças não esperadas. Nenhuma rota que respondia 200 passou a responder 401/403.

### Pendências conhecidas (assumidas de propósito)

| Item | Onde | Por quê |
|---|---|---|
| Ausência de autenticação nas rotas (AP-06) — no projeto 2 o finding é CRITICAL | 3 projetos | Exigir login transformaria requisições hoje bem-sucedidas em 401, o que precisa de decisão de produto. A parte corrigível desse mesmo finding **foi fechada**: endpoints destrutivos e administrativos (`/admin/*` no projeto 1, relatório financeiro e `DELETE /api/users/:id` no projeto 2, `DELETE /users/<id>` no projeto 3) ficam 403 por padrão e só abrem com `ADMIN_ENDPOINTS_ENABLED` + `ADMIN_TOKEN`; e nenhum campo de privilégio (`role`, `active`) é mais aceito de cliente anônimo |
| Rotas comuns do domínio seguem públicas | 3 projetos | Mesmo motivo acima: `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `PUT`/`DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` (projeto 1), `PUT /tasks/<id>` etc. continuam sem autenticação, como no original. Desde a v1.5.1 essa regra está explícita nas guidelines da skill |
| Política de senha mais dura muda o cadastro | code-smells-project, task-manager-api | Mínimo de 8 caracteres foi aplicado (era 4/nenhum); contas antigas continuam autenticando, mas cadastros com senha curta agora recebem 400 |
| Sem testes automatizados | 3 projetos | Fora do escopo do desafio; o smoke test e as provas de segurança do repositório cobrem o contrato |

---

## D) Como Executar

### Pré-requisitos

| Ferramenta | Versão usada | Observação |
|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/overview) | 2.1.273 (execuções originais) · 2.1.280 (reexecução v1.5.1) | `curl -fsSL https://claude.ai/install.sh \| bash`, depois `claude` para fazer login |
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
# Fases 1-2 (somente leitura); o turno termina na pergunta de confirmação
claude -p "/refactor-arch" --strict-mcp-config --output-format json > fase12.json
python3 -c "import json; print(json.load(open('fase12.json'))['result'])"          # lê o relatório
SESSION=$(python3 -c "import json; print(json.load(open('fase12.json'))['session_id'])")
# Fase 3, retomando a mesma sessão
claude -p "y" --resume "$SESSION" --strict-mcp-config
```

> Notas sobre o modo headless: usei `--strict-mcp-config` para não carregar os servidores MCP do meu ambiente (os avisos deles poluíam a saída) e `--output-format stream-json --verbose` para gravar a linha do tempo completa que está em `docs/execution-logs/`. Como em `-p` não há aprovação interativa de permissões, a Fase 3 precisa de um modo de permissão que aceite escrita — aqui o `settings.json` da máquina já usava `defaultMode: auto` e nenhuma permissão foi negada (`permission_denials: []` em todas as sessões); em uma máquina com o padrão, acrescente `--permission-mode acceptEdits --allowedTools "Bash"`.

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
scripts/validate.sh all          # ou: scripts/validate.sh 1 | 2 | 3
scripts/validate.sh all --save   # também atualiza os resultados em docs/validation/
scripts/security_probes.sh all   # 38 provas de segurança com as aplicações no ar
```

O script termina com código `0` só se as 3 aplicações subirem, os logs ficarem sem traceback e todas as diferenças em relação ao código original estiverem declaradas em `docs/validation/expected-differences.json`.

Validação manual:

```bash
# Projeto 1
cd code-smells-project && pip install -r requirements.txt
SEED_PASSWORD=admin123 python app.py      # sem SEED_PASSWORD o seed sorteia a senha e a mostra uma vez no log
curl localhost:5000/health
curl "localhost:5000/produtos/busca?q=Mouse"
curl -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"admin@loja.com","senha":"admin123"}'
# cancelar devolve o estoque: veja o estoque do produto 2, faça um pedido, cancele e veja de novo
curl localhost:5000/produtos/2
curl -X POST localhost:5000/pedidos -H 'Content-Type: application/json' -d '{"usuario_id":1,"itens":[{"produto_id":2,"quantidade":3}]}'
curl -X PUT localhost:5000/pedidos/1/status -H 'Content-Type: application/json' -d '{"status":"cancelado"}'
curl localhost:5000/produtos/2

# Projeto 2
cd ecommerce-api-legacy && npm install && npm start
curl -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
     -d '{"usr":"Ana","eml":"ana@teste.com","pwd":"segredo","c_id":2,"card":"4111222233334444"}'
curl localhost:3000/api/admin/financial-report          # 403: rota administrativa fechada por padrão
# para abri-la: ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=segredo npm start
curl -H 'X-Admin-Token: segredo' localhost:3000/api/admin/financial-report   # ou use api.http

# Projeto 3
cd task-manager-api && pip install -r requirements.txt
SEED_PASSWORD=senha1234 python seed.py && python app.py   # seed sem senha fixa (mínimo 8 caracteres)
curl localhost:5000/tasks
curl localhost:5000/reports/summary
curl -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"joao@email.com","password":"senha1234"}'
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
│   ├── audit-project-1.md           # saída da Fase 2 sobre o código legado (verbatim)
│   ├── audit-project-2.md
│   ├── audit-project-3.md
│   └── audit-project-*-rerun*.md    # reauditorias do código já refatorado (iteração pós-avaliação)
├── docs/
│   ├── ENUNCIADO.md                 # enunciado original do desafio
│   ├── execution-logs/              # saída das Fases 1 e 3 + linha do tempo de ferramentas, por projeto
│   └── validation/                  # baseline do código original, resultados pós-refatoração,
│                                    # comparações, logs dos servidores e expected-differences.json
└── scripts/
    ├── smoke_test.py                # exercita todos os endpoints de um projeto
    ├── compare_results.py           # compara baseline × refatorado (status + shape), com gate de regressão
    ├── check_report_locations.py    # confere os arquivo:linha dos relatórios contra o código original
    ├── security_probes.sh           # provas de segurança com as aplicações no ar
    └── validate.sh                  # validação ponta a ponta dos 3 projetos
```
