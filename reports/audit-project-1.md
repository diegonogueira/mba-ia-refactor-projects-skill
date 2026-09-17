# Audit Report — code-smells-project

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.2.0), gerada por `claude -p "/refactor-arch"` executado dentro de `code-smells-project/`
> (modelo `claude-opus-5[1m]`, sessão `af8ff879-a7ae-47da-8c87-e824e7365578`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 6 · HIGH 8 · MEDIUM 7 · LOW 5 · Total 26.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
```

## Summary

CRITICAL: 6 | HIGH: 8 | MEDIUM: 7 | LOW: 5

## Findings

### [CRITICAL] God Module — sem separação de responsabilidades
- **ID:** AP-03
- **File:** `app.py:1-88`, `controllers.py:1-292`, `models.py:1-314`
- **Description:** Os três arquivos da raiz levam nomes de camada, mas misturam responsabilidades. `app.py` concentra configuração (`SECRET_KEY`, `DEBUG`, `CORS`), todas as rotas e handlers com SQL direto (`reset_database`, `executar_query`). `controllers.py` junta HTTP, validação, listas de domínio (`categorias_validas`, lista de status), "notificações" (`ENVIANDO EMAIL/SMS/PUSH`) e SQL direto em `health_check`. `models.py` guarda as queries das 4 entidades junto com regras de negócio: checagem de estoque e cálculo do total em `criar_pedido`, faixas de desconto em `relatorio_vendas`, além da serialização.
- **Impact:** Não há onde colocar uma regra sem mexer em HTTP e SQL ao mesmo tempo. Não dá para testar as regras isoladamente, e qualquer mudança se espalha pelos três arquivos.
- **Recommendation:** Separar em `config/`, `models/` (acesso a dados por entidade), `services/` (caso de uso do pedido), `controllers/` (fluxo HTTP), `views/` (rotas e serializers) e `middlewares/` (erros), montados por um app factory. (Playbook T-03)

### [CRITICAL] Hardcoded Credentials and Secrets
- **ID:** AP-01
- **File:** `app.py:7`, `controllers.py:289`, `database.py:76`
- **Description:** A chave `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` está fixa no código, e o mesmo literal se repete na resposta do `health_check`. O seed cria o usuário administrador com senha fixa: `("Admin", "admin@loja.com", "admin123", "admin")`.
- **Impact:** Quem lê o repositório consegue forjar sessões assinadas com a chave e entrar como administrador com a senha conhecida. Trocar o segredo exige um novo deploy de código.
- **Recommendation:** Ler `SECRET_KEY` de variável de ambiente (gerando um valor aleatório quando ausente), criar `.env.example` sem valores reais e não enviar credenciais conhecidas no seed. (Playbook T-01)

### [CRITICAL] Unprotected Destructive Endpoints — execução de SQL arbitrário e reset do banco
- **ID:** AP-06
- **File:** `app.py:47-57`, `app.py:59-78`
- **Description:** `POST /admin/query` executa `cursor.execute(query)` com `dados.get("sql")` vindo direto do corpo da requisição e faz `commit()` quando o comando não é SELECT. `POST /admin/reset-db` roda `DELETE FROM` em `itens_pedido`, `pedidos`, `produtos` e `usuarios`. Nenhuma das duas rotas tem autenticação ou autorização.
- **Impact:** Qualquer cliente de rede pode ler, alterar ou apagar o banco inteiro (inclusive senhas) com uma única requisição.
- **Recommendation:** Remover o executor de SQL arbitrário. Proteger o reset com um guard de token administrativo vindo de configuração e desabilitá-lo por padrão fora de desenvolvimento. (Playbook T-06)

### [CRITICAL] Sensitive Data Exposure — senhas e segredos nas respostas
- **ID:** AP-04
- **File:** `controllers.py:276-290`, `models.py:83`, `models.py:99`
- **Description:** `get_todos_usuarios()` e `get_usuario_por_id()` serializam `"senha": row["senha"]`, e `GET /usuarios` e `GET /usuarios/<id>` devolvem esses dados sem proteção. O `GET /health` retorna `"secret_key": "minha-chave-super-secreta-123"`, `"debug": True` e `"db_path": "loja.db"`.
- **Impact:** Qualquer pessoa obtém as senhas de todos os usuários (em texto puro, ver AP-05) e a chave de assinatura da aplicação.
- **Recommendation:** Criar serializers de usuário sem campo de senha e limitar o `/health` a status, banco e contagens, sem configuração interna. (Playbook T-05)

### [CRITICAL] Insecure Password Storage
- **ID:** AP-05
- **File:** `database.py:75-83`, `models.py:109-111`, `models.py:126-129`
- **Description:** `criar_usuario()` grava `senha` exatamente como recebida (`INSERT INTO usuarios ... '" + senha + "'`). `login_usuario()` compara a senha em texto puro dentro do SQL (`WHERE email = '...' AND senha = '...'`), e o seed insere senhas em texto puro (`"admin123"`, `"123456"`, `"senha123"`). Também não existe tamanho mínimo de senha (`controllers.py:157` só checa se está vazia).
- **Impact:** Um vazamento do banco (trivial via AP-02, AP-04 ou AP-06) expõe todas as credenciais, que costumam ser reutilizadas em outros serviços.
- **Recommendation:** Guardar hash com `werkzeug.security.generate_password_hash` e validar com `check_password_hash` no model. O seed deve gravar hashes. (Playbook T-04)

### [CRITICAL] SQL Injection
- **ID:** AP-02
- **File:** `models.py:28`, `models.py:47-50`, `models.py:57-61`, `models.py:68`, `models.py:92`, `models.py:109-111`, `models.py:126-129`, `models.py:140`, `models.py:148-151`, `models.py:155`, `models.py:157-161`, `models.py:163-166`, `models.py:174`, `models.py:188`, `models.py:192`, `models.py:220`, `models.py:224`, `models.py:279-281`, `models.py:289-299`
- **Description:** Todas as queries com parâmetros são montadas por concatenação. Exemplos: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` em `login_usuario()`; `query += " AND (nome LIKE '%" + termo + "%' ..."` e `" AND categoria = '" + categoria + "'"` em `buscar_produtos()`; `INSERT`/`UPDATE` de produtos com `nome` e `descricao` do corpo JSON; `item["produto_id"]` e `usuario_id` do JSON em `criar_pedido()`.
- **Impact:** `POST /login` com `email = "admin@loja.com' --"` entra como administrador sem senha. `GET /produtos/busca?q=...` permite ler qualquer tabela via `UNION`. Um nome com apóstrofo (ex.: `"Pão d'água"`) quebra o cadastro com erro 500.
- **Recommendation:** Usar placeholders `?` com parâmetros em todas as queries e montar filtros dinâmicos só com fragmentos constantes. (Playbook T-02)

### [HIGH] Tight Coupling / No Composition Root
- **ID:** AP-08
- **File:** `app.py:3-9`, `controllers.py:2-3`, `database.py:7-86`, `models.py:1`
- **Description:** O `app = Flask(__name__)` é criado e configurado no momento do import, sem app factory. Controllers e models importam a conexão global (`from database import get_db`). A primeira chamada a `get_db()` tem efeito colateral: cria o schema e insere o seed.
- **Impact:** Não dá para subir a aplicação com outro banco ou configuração (testes, ambientes), e os módulos ficam presos ao arquivo `loja.db`.
- **Recommendation:** Criar `create_app(config)` que registra blueprints, error handlers e extensões. Gerenciar a conexão por requisição (`flask.g`) e mover schema e seed para uma função de inicialização chamada pelo factory. (Playbook T-11)

### [HIGH] Insecure Runtime Configuration
- **ID:** AP-10
- **File:** `app.py:8`, `app.py:9`, `app.py:88`, `controllers.py:286-288`
- **Description:** `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` expõem o debugger interativo do Werkzeug em todas as interfaces. `CORS(app)` é aplicado sem restringir `origins`. O `health_check` declara `"ambiente": "producao"` com `"debug": True`.
- **Impact:** O debugger do Werkzeug permite execução remota de código quando acessível pela rede, e o CORS aberto deixa qualquer site chamar a API.
- **Recommendation:** Ler `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` de variáveis de ambiente, com padrões seguros (debug desligado). (Playbook T-01)

### [HIGH] Broken Authentication — rotas de gestão sem autenticação/autorização
- **ID:** AP-06
- **File:** `app.py:15-16`, `app.py:18`, `app.py:24`, `app.py:26`, `app.py:28`, `controllers.py:176-180`
- **Description:** `POST /login` apenas devolve os dados do usuário, sem emitir token ou sessão. Por isso nenhuma rota consegue verificar identidade ou papel (`tipo`): qualquer cliente pode alterar ou excluir produtos (`PUT`/`DELETE /produtos/<id>`), listar todos os usuários (`GET /usuarios`), listar todos os pedidos (`GET /pedidos`), mudar o status de pedidos (`PUT /pedidos/<id>/status`) e ler o relatório financeiro (`GET /relatorios/vendas`).
- **Impact:** Não existe controle de acesso: um cliente anônimo executa operações de administrador.
- **Recommendation:** Introduzir autenticação com token assinado e guards por papel (`admin`) nas rotas de gestão. Isso muda o contrato público e depende de decisão de produto. (Playbook T-06)

### [HIGH] Business Logic in Controllers (fat controller)
- **ID:** AP-07
- **File:** `controllers.py:24-62`, `controllers.py:188-220`, `controllers.py:237-255`, `controllers.py:264-290`
- **Description:** `criar_produto()` tem 39 linhas com a cadeia de validação e a lista `categorias_validas`. `criar_pedido()` dispara efeitos colaterais inline (`print("ENVIANDO EMAIL: ...")`, `ENVIANDO SMS`, `ENVIANDO PUSH`). `atualizar_status_pedido()` guarda a lista de status válidos e as notificações por status (`"cancelado. Devolver estoque."` só imprime, o estoque não é devolvido). `health_check()` executa `cursor.execute("SELECT COUNT(*) ...")` direto no controller.
- **Impact:** As regras de domínio e as notificações ficam presas ao HTTP. Não podem ser reutilizadas nem testadas sem requisição, e a regra "cancelar devolve estoque" está documentada mas não implementada.
- **Recommendation:** Levar validação e regras de entidade para os models, o fluxo do pedido e as notificações para `services/`, e deixar os controllers só com entrada → chamada → resposta. (Playbook T-03, T-13)

### [HIGH] Missing Input Validation — itens do pedido corrompem o estoque
- **ID:** AP-14
- **File:** `controllers.py:195-201`, `models.py:139-146`, `models.py:163-166`
- **Description:** `criar_pedido()` só verifica se `itens` não está vazio. `quantidade` não tem checagem de tipo nem de positividade, e as chaves `produto_id`/`quantidade` não são verificadas. Com `quantidade = -5`, o teste `produto["estoque"] < item["quantidade"]` passa, e `UPDATE produtos SET estoque = estoque - -5` aumenta o estoque.
- **Impact:** Um pedido com quantidade negativa gera total negativo, infla o estoque e distorce o faturamento. Um item sem `quantidade` causa `KeyError` → HTTP 500.
- **Recommendation:** Validar cada item (`produto_id` e `quantidade` inteiros, `quantidade > 0`) antes de chamar o serviço de pedidos e responder 400 com mensagem clara. (Playbook T-12)

### [HIGH] Mutable Global State
- **ID:** AP-09
- **File:** `database.py:4-11`
- **Description:** A variável de módulo `db_connection = None` é alterada via `global db_connection`, e uma única conexão `sqlite3.connect(db_path, check_same_thread=False)` é compartilhada por todas as requisições e threads do servidor.
- **Impact:** Requisições concorrentes dividem a mesma transação implícita: um `commit()` de uma requisição grava escritas pela metade de outra, e há risco de `ProgrammingError`/`database is locked` sob carga.
- **Recommendation:** Abrir uma conexão por requisição (`flask.g`) e fechá-la em `teardown_appcontext`, com o caminho do banco vindo da configuração. (Playbook T-11, T-18)

### [HIGH] Non-Atomic Multi-Step Writes
- **ID:** AP-11
- **File:** `models.py:139-146`, `models.py:148-168`
- **Description:** `criar_pedido()` lê o estoque (`SELECT * FROM produtos`), compara em Python e só depois faz `INSERT INTO pedidos`, N `INSERT INTO itens_pedido` e N `UPDATE produtos SET estoque = estoque - n`. Não há `BEGIN`/`ROLLBACK` nem update condicional. Se uma exceção ocorrer entre o `INSERT` do pedido e o `commit()` da linha 168, a transação pendente não é desfeita e vai ser confirmada pelo próximo `commit()` de qualquer requisição.
- **Impact:** Pedidos sem itens ou estoque parcialmente baixado. Dois pedidos simultâneos podem passar pela checagem e deixar o estoque negativo (overselling).
- **Recommendation:** Rodar a operação dentro de uma transação explícita (`with conn:` com rollback em erro) e baixar o estoque com update condicional (`WHERE id = ? AND estoque >= ?`), conferindo `rowcount`. (Playbook T-09)

### [HIGH] Vulnerable Dependencies
- **ID:** AP-18
- **File:** `requirements.txt:1`, `requirements.txt:2`
- **Description:** A consulta à API JSON do PyPI mostrou vulnerabilidades nas duas dependências usadas em runtime. `flask==3.1.1` tem CVE-2026-27205 / GHSA-68rp-wp8r-4726 (falta de `Vary: Cookie` ao acessar `session`), corrigida em 3.1.3. `flask-cors==5.0.1` tem CVE-2024-6866 (path matching case-insensitive), CVE-2024-6844 (tratamento de `+` no path) e CVE-2024-6839 (prioridade incorreta de regex), corrigidas em 6.0.0.
- **Impact:** As regras de CORS podem casar com caminhos diferentes do esperado. A falha do Flask afeta respostas que usam `session` (a aplicação hoje não usa, o que reduz a exposição).
- **Recommendation:** Atualizar para `flask==3.1.3` (patch, sem quebra) e `flask-cors>=6.0.0` (última: 6.0.5), validando o comportamento do CORS. (Playbook T-14)

### [MEDIUM] Missing Input Validation — tipos, payload e consistência create/update
- **ID:** AP-14
- **File:** `app.py:61-62`, `controllers.py:43-50`, `controllers.py:81-90`, `controllers.py:118-121`, `controllers.py:153-158`, `controllers.py:169-170`, `controllers.py:239-245`
- **Description:** Vários caminhos quebram ou aceitam dados inválidos:
  - `preco < 0` e `len(nome)` rodam sem checar tipo (`"preco": "abc"` → `TypeError`).
  - `atualizar_produto()` não aplica as regras de tamanho do nome nem `categorias_validas`, que existem no create.
  - `float(preco_min)` gera `ValueError` com entrada não numérica.
  - `criar_usuario()` não valida formato de e-mail nem duplicidade.
  - `login()`, `atualizar_status_pedido()` e `executar_query()` chamam `dados.get(...)` sem checar `None`.
  - `atualizar_status_pedido()` responde 200 para pedido inexistente.
- **Impact:** Entradas inválidas comuns resultam em HTTP 500 em vez de 400/404, e a atualização aceita produtos que o cadastro rejeitaria.
- **Recommendation:** Centralizar validadores por entidade (mesmas regras em create e update), checar tipos e payload JSON e responder 400/404 de forma consistente. (Playbook T-12)

### [MEDIUM] Generic Exception Handling, No Centralized Error Handler
- **ID:** AP-15
- **File:** `app.py:77-78`, `controllers.py:10-12`, `controllers.py:21-22`, `controllers.py:60-62`, `controllers.py:95-96`, `controllers.py:108-109`, `controllers.py:125-126`, `controllers.py:133-134`, `controllers.py:143-144`, `controllers.py:164-165`, `controllers.py:185-186`, `controllers.py:218-220`, `controllers.py:226-227`, `controllers.py:234-235`, `controllers.py:254-255`, `controllers.py:261-262`, `controllers.py:291-292`
- **Description:** Os 16 handlers de `controllers.py` e `executar_query()` repetem `except Exception as e: return jsonify({"erro": str(e)}), 500`. Não existe `@app.errorhandler`.
- **Impact:** Mensagens internas (SQL, tracebacks resumidos, detalhes do schema) chegam ao cliente, erros de validação viram 500 e o tratamento está copiado 17 vezes.
- **Recommendation:** Criar exceções de domínio (`ValidationError`, `NotFoundError`) e um error handler central que responde JSON padronizado e registra o erro no log sem expor detalhes internos. (Playbook T-07)

### [MEDIUM] Inconsistent Response Envelopes
- **ID:** AP-19
- **File:** `app.py:64`, `controllers.py:20`, `controllers.py:29`, `controllers.py:142`, `controllers.py:183`, `controllers.py:206`, `controllers.py:292`
- **Description:** Os erros usam formatos diferentes: `{"erro": ..., "sucesso": False}` (`controllers.py:20`, `183`, `206`), `{"erro": ...}` sem `sucesso` (`controllers.py:29`, `142`, `app.py:64`) e `{"status": "erro", "detalhes": ...}` no health (`controllers.py:292`). 404/405 de rotas inexistentes caem no HTML padrão do Flask. Preocupações transversais (try/except, logging) se repetem em cada handler em vez de middleware.
- **Impact:** O cliente precisa tratar vários formatos de erro, e as respostas HTML quebram consumidores JSON.
- **Recommendation:** Concentrar a montagem das respostas de erro no error handler central (mantendo o campo `erro` do contrato) e registrar handlers JSON para 404/405. (Playbook T-07)

### [MEDIUM] Code Duplication
- **ID:** AP-16
- **File:** `controllers.py:28-35`, `controllers.py:43-46`, `controllers.py:72-79`, `controllers.py:87-90`, `models.py:12-21`, `models.py:31-40`, `models.py:79-86`, `models.py:95-102`, `models.py:178-199`, `models.py:211-231`, `models.py:304-313`
- **Description:** Há três blocos repetidos:
  - A cadeia de validação de produto (`"nome" not in dados`, `preco < 0`...) aparece em `criar_produto` e `atualizar_produto`.
  - O mapeamento de linha para dict de produto se repete 3 vezes, e o de usuário 2 vezes.
  - `get_pedidos_usuario()` e `get_todos_pedidos()` são idênticas, exceto pelo `WHERE`.
- **Impact:** As correções precisam ser replicadas à mão. A divergência já aconteceu: a validação de categoria existe só no create.
- **Recommendation:** Extrair serializers únicos por entidade, um validador de produto compartilhado e uma função de listagem de pedidos com filtro opcional. (Playbook T-13)

### [MEDIUM] Sensitive Data Exposure — PII em logs
- **ID:** AP-04
- **File:** `controllers.py:161`, `controllers.py:179`, `controllers.py:182`
- **Description:** `print("Usuário criado: " + email)`, `print("Login bem-sucedido: " + email)` e `print("Login falhou: " + email)` gravam e-mails no stdout sem mascaramento.
- **Impact:** Dados pessoais vão parar em logs de infraestrutura, e as tentativas de login falhas identificam contas válidas.
- **Recommendation:** Usar `logging` com e-mail mascarado ou só o ID do usuário. (Playbook T-05)

### [MEDIUM] N+1 Queries and Per-Row Aggregation
- **ID:** AP-13
- **File:** `controllers.py:269-274`, `models.py:186-199`, `models.py:219-231`, `models.py:239-254`
- **Description:** `get_pedidos_usuario()` e `get_todos_pedidos()` rodam `SELECT * FROM itens_pedido` para cada pedido (`cursor2`) e `SELECT nome FROM produtos` para cada item (`cursor3`). `relatorio_vendas()` faz 5 consultas separadas (`COUNT`, `SUM` e 3 `COUNT ... WHERE status`), e `health_check()` faz 3 `COUNT(*)` avulsos.
- **Impact:** A listagem de pedidos cresce para 1 + P + I queries: com 1.000 pedidos de 3 itens são mais de 4.000 consultas por requisição.
- **Recommendation:** Buscar os itens com `JOIN produtos` e `pedido_id IN (...)` (ou uma query só, agrupando em Python) e calcular o relatório numa consulta com `SUM(CASE WHEN ...)`. (Playbook T-08)

### [MEDIUM] Broken Referential Integrity on Delete
- **ID:** AP-12
- **File:** `database.py:36-53`, `models.py:65-70`, `models.py:196`, `models.py:228`
- **Description:** As tabelas `pedidos.usuario_id` e `itens_pedido.pedido_id/produto_id` não declaram `FOREIGN KEY`. `deletar_produto()` executa `DELETE FROM produtos WHERE id = ...` mesmo com itens de pedido referenciando o produto, e as listagens contornam o órfão com `"produto_nome": ... else "Desconhecido"`. `criar_pedido()` também aceita `usuario_id` inexistente.
- **Impact:** O histórico de pedidos perde a referência ao produto e podem surgir pedidos de usuários que não existem. Relatórios e totais não são afetados, pois `total` fica em `pedidos`.
- **Recommendation:** Verificar se o usuário existe ao criar pedido e impedir a exclusão de produto referenciado por pedidos (ou fazer soft delete via coluna `ativo`, que já existe), documentando a decisão. (Playbook T-17)

### [LOW] print Logging Instead of a Logger
- **ID:** AP-23
- **File:** `app.py:56`, `app.py:83-86`, `controllers.py:8`, `controllers.py:11`, `controllers.py:57`, `controllers.py:61`, `controllers.py:106`, `controllers.py:208-210`, `controllers.py:219`, `controllers.py:248`, `controllers.py:250`
- **Description:** O log usa `print` sem nível nem configuração (`"Listando " + str(len(produtos)) + " produtos"`, `"ERRO CRITICO ao criar pedido: "`), e os efeitos colaterais de negócio são simulados com `print("ENVIANDO EMAIL: ...")` e `print("NOTIFICAÇÃO: ...")`.
- **Impact:** Não dá para filtrar por severidade nem desligar logs de debug, e as notificações "falsas" ficam misturadas ao log.
- **Recommendation:** Usar `logging.getLogger(__name__)` com níveis e colocar as notificações num serviço de notificação dedicado. (Playbook T-16)

### [LOW] Magic Numbers and Strings
- **ID:** AP-20
- **File:** `app.py:36`, `app.py:88`, `controllers.py:47-50`, `controllers.py:52`, `controllers.py:242`, `controllers.py:285`, `database.py:5`, `models.py:150`, `models.py:247-253`, `models.py:257-262`
- **Description:** O código tem literais soltos:
  - Faixas de desconto `10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`.
  - Limites de nome `2` e `200`, porta `5000`, arquivo `"loja.db"` e versão `"1.0.0"` repetida.
  - A lista de categorias e os status `'pendente'`, `'aprovado'` e `'cancelado'` espalhados por controllers e models.
- **Impact:** Mudar uma regra comercial ou um status exige caçar literais em vários arquivos, com risco de inconsistência.
- **Recommendation:** Definir constantes nomeadas no model de cada domínio (`CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, faixas de desconto) e ler porta e caminho do banco da configuração. (Playbook T-15)

### [LOW] Poor Naming
- **ID:** AP-21
- **File:** `controllers.py:14`, `controllers.py:56`, `controllers.py:64`, `controllers.py:98`, `controllers.py:136`, `controllers.py:160`, `models.py:24`, `models.py:54`, `models.py:65`, `models.py:89`, `models.py:187`, `models.py:191`, `models.py:193`, `models.py:219`, `models.py:223`, `models.py:225`
- **Description:** Parâmetros e variáveis chamados `id` sombreiam o builtin, e há nomes sem significado como `cursor2`, `cursor3` e `prod`.
- **Impact:** A leitura fica mais difícil e o builtin `id()` pode ser usado por engano no mesmo escopo.
- **Recommendation:** Renomear internamente para `produto_id`, `usuario_id`, `itens_cursor` e similares, mantendo o nome do parâmetro de rota no contrato. (Playbook T-15)

### [LOW] Verbose / Non-Idiomatic Conditionals
- **ID:** AP-24
- **File:** `controllers.py:200`, `models.py:242-245`
- **Description:** `if not itens or len(itens) == 0` checa vazio duas vezes, e `faturamento = cursor.fetchone()[0]` seguido de `if faturamento is None: faturamento = 0` poderia ser `COALESCE(SUM(total), 0)` no SQL.
- **Impact:** Ruído que dificulta a leitura das regras.
- **Recommendation:** Simplificar para `if not itens` e usar `COALESCE` na agregação. (Playbook T-16)

### [LOW] Dead Code and Unused Imports
- **ID:** AP-22
- **File:** `database.py:2`, `models.py:2`, `models.py:63`, `models.py:70`, `models.py:122`, `models.py:283`
- **Description:** `import os` (database.py) e `import sqlite3` (models.py) nunca são usados. `atualizar_produto`, `deletar_produto` e `atualizar_status_pedido` retornam `True`, e nenhum chamador usa o valor. O parâmetro `tipo="cliente"` de `criar_usuario()` nunca é informado.
- **Impact:** Ruído e falsa impressão de que existem dependências e opções que não são usadas.
- **Recommendation:** Remover imports e retornos não usados e manter só parâmetros com uso real. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `requirements.txt:1` | `flask==3.1.1` — CVE-2026-27205 / GHSA-68rp-wp8r-4726 (sem `Vary: Cookie` ao acessar `session`) | `flask==3.1.3` |
| `requirements.txt:2` | `flask-cors==5.0.1` — CVE-2024-6866, CVE-2024-6844, CVE-2024-6839 (path matching incorreto) | `flask-cors>=6.0.0` (última 6.0.5) |

No código não encontrei nenhuma API da tabela de obsoletas (`utcnow`, `before_first_request`, `JSONEncoder`, `pkg_resources` etc.) para as versões detectadas. Os itens acima vêm da auditoria de dependências no PyPI.

```text
================================
Total: 26 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
