# Audit Report — code-smells-project

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.1.0), gerada por `claude -p "/refactor-arch"` executado dentro de `code-smells-project/`
> (modelo `claude-opus-5[1m]`, sessão `f2b201e7-958d-4d2c-b506-fa8629e6fa03`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 6 · HIGH 7 · MEDIUM 7 · LOW 5 · Total 25.

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

CRITICAL: 6 | HIGH: 7 | MEDIUM: 7 | LOW: 5

## Findings

### [CRITICAL] God Class / God Module
- **ID:** AP-03
- **File:** `app.py:6-88`, `controllers.py:1-292`, `database.py:7-86`, `models.py:1-314`
- **Description:** Não existem camadas de verdade, só 4 arquivos na raiz, e cada um mistura várias responsabilidades:
  - `app.py` reúne configuração (`app.config["SECRET_KEY"]`, `CORS(app)`), a tabela de rotas, handlers com SQL inline (`reset_database`, `executar_query`) e a inicialização do servidor;
  - `controllers.py` mistura HTTP (`request.get_json`, `jsonify`), validação, regras de negócio (lista de categorias, lista de status), notificações simuladas e SQL direto em `health_check()`;
  - `models.py` concentra o SQL das 4 tabelas, regras de negócio (checagem de estoque e cálculo de total em `criar_pedido()`, faixas de desconto em `relatorio_vendas()`) e a conversão manual de linhas em dict;
  - `database.py` → `get_db()` abre a conexão, cria o schema (`CREATE TABLE IF NOT EXISTS ...`) e insere o seed.
- **Impact:** Qualquer mudança espalha efeitos por vários arquivos. Não dá para testar regras de negócio sem Flask e sem o `loja.db` real, e cada nova entidade só piora o acoplamento.
- **Recommendation:** Reorganizar em `config/`, `models/`, `services/`, `controllers/`, `views/` (rotas) e `middlewares/`, todos ligados por uma app factory. (Playbook T-03)

### [CRITICAL] Hardcoded Credentials and Secrets
- **ID:** AP-01
- **File:** `app.py:7`, `controllers.py:289`, `database.py:76-78`
- **Description:** `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` está escrito direto no código, e o mesmo valor volta na resposta de `/health`. O seed cria o administrador `("Admin", "admin@loja.com", "admin123", "admin")` e usuários com as senhas `"123456"` e `"senha123"` fixas no código.
- **Impact:** Quem tem acesso ao repositório ou a `GET /health` obtém a chave de assinatura da aplicação e uma credencial de admin válida. A chave também não pode ser trocada por ambiente.
- **Recommendation:** Ler `SECRET_KEY` de variável de ambiente, sem default secreto, e criar um `.env.example` com placeholders. As senhas do seed devem ficar só para desenvolvimento e ser gravadas com hash. Tirar a chave da resposta de `/health`. (Playbook T-01)

### [CRITICAL] Unprotected Destructive/Debug Endpoints
- **ID:** AP-06
- **File:** `app.py:47-57`, `app.py:59-78`
- **Description:** `POST /admin/query` pega `dados.get("sql", "")` e roda com `cursor.execute(query)`, fazendo `db.commit()` em tudo que não for `SELECT`. `POST /admin/reset-db` executa `DELETE FROM` em `itens_pedido`, `pedidos`, `produtos` e `usuarios`. Nenhuma das duas rotas exige autenticação ou autorização.
- **Impact:** Qualquer cliente anônimo pode ler (`{"sql": "SELECT email, senha FROM usuarios"}`), alterar ou destruir o banco inteiro remotamente (`{"sql": "DROP TABLE pedidos"}`).
- **Recommendation:** Remover o executor de SQL arbitrário. Proteger o reset com um guard (token vindo da configuração) e deixá-lo desligado por padrão fora de desenvolvimento. (Playbook T-06)

### [CRITICAL] Insecure Password Storage
- **ID:** AP-05
- **File:** `controllers.py:155-158`, `database.py:75-83`, `models.py:109-111`, `models.py:126-129`
- **Description:** As senhas ficam em texto puro:
  - `criar_usuario()` grava `senha` exatamente como chega;
  - `login_usuario()` compara a senha dentro do SQL (`"... AND senha = '" + senha + "'"`);
  - o seed insere `"admin123"`, `"123456"` e `"senha123"` sem hash;
  - o controller só testa `not senha`, então uma senha de 1 caractere é aceita.
- **Impact:** Qualquer vazamento (por `/admin/query`, `GET /usuarios` ou uma cópia do `loja.db`) expõe as senhas reais de todos os usuários, que costumam ser reaproveitadas em outros serviços.
- **Recommendation:** Usar `werkzeug.security.generate_password_hash` / `check_password_hash`: buscar o usuário pelo e-mail e verificar o hash na aplicação. Gravar o seed com hash e definir um tamanho mínimo de senha. (Playbook T-04)

### [CRITICAL] Sensitive Data Exposure — responses
- **ID:** AP-04
- **File:** `controllers.py:285-289`, `models.py:83`, `models.py:99`
- **Description:** `GET /health` devolve `"secret_key": "minha-chave-super-secreta-123"`, `"debug": True`, `"db_path": "loja.db"` e `"ambiente": "producao"`. `get_todos_usuarios()` e `get_usuario_por_id()` montam o dict com `"senha": row["senha"]`, então `GET /usuarios` e `GET /usuarios/<id>` devolvem a senha de todo mundo.
- **Impact:** Sem autenticação, qualquer pessoa obtém todas as credenciais (em texto puro) e a chave de assinatura da aplicação.
- **Recommendation:** Usar serializers com lista explícita de campos permitidos (usuário sem `senha`). `/health` deve devolver só status, conexão e contagens. (Playbook T-05)

### [CRITICAL] SQL Injection
- **ID:** AP-02
- **File:** `models.py:28`, `models.py:47-50`, `models.py:57-61`, `models.py:68`, `models.py:92`, `models.py:109-111`, `models.py:126-129`, `models.py:140`, `models.py:148-151`, `models.py:155`, `models.py:157-166`, `models.py:174`, `models.py:188`, `models.py:192`, `models.py:220`, `models.py:224`, `models.py:279-281`, `models.py:289-299`
- **Description:** Todas as queries de `models.py` são montadas concatenando strings. Exemplos:
  - `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` em `login_usuario()`;
  - `query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"` e `" AND categoria = '" + categoria + "'"` em `buscar_produtos()`;
  - `INSERT`/`UPDATE` de produtos e usuários com `nome`, `descricao`, `categoria`, `email` e `senha` vindos do body;
  - `criar_pedido()` usando `item["produto_id"]` e `item["quantidade"]` do JSON sem nenhuma conversão.
- **Impact:** `POST /login` com `{"email": "' OR 1=1 --", "senha": "x"}` loga como o primeiro usuário (Admin). `GET /produtos/busca?q=` aceita `UNION SELECT` para ler a tabela `usuarios`. Até valores legítimos com apóstrofo (`"Pão d'água"`) quebram o INSERT e dão 500.
- **Recommendation:** Usar placeholders `?` com parâmetros em todas as queries. Em `buscar_produtos()`, concatenar só fragmentos constantes e juntar os valores numa lista de parâmetros. (Playbook T-02)

### [HIGH] Tight Coupling Without Dependency Injection
- **ID:** AP-08
- **File:** `app.py:3-4`, `app.py:6-9`, `controllers.py:2-3`, `database.py:7-86`, `models.py:1`
- **Description:** Não há app factory: `app = Flask(__name__)` é criado e configurado no momento do import. `controllers.py` importa direto o módulo `models` e o `get_db` global, e `models.py` faz `from database import get_db`. A primeira chamada de `get_db()` cria o schema e insere o seed, um efeito colateral escondido dentro do acesso a dados.
- **Impact:** Não dá para subir a aplicação com outra configuração ou com um banco de teste. Os testes dependem do `loja.db` real, e o comportamento depende da ordem dos imports.
- **Recommendation:** Criar `create_app(config)` como composition root, com a conexão vinda da configuração e inicialização explícita de schema e seed chamada pela factory. (Playbook T-11)

### [HIGH] Insecure Runtime Configuration
- **ID:** AP-10
- **File:** `app.py:8-9`, `app.py:88`, `controllers.py:286-288`
- **Description:** `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` estão fixos no código. `CORS(app)` não define `origins`, então qualquer origem é aceita. `/health` anuncia `"ambiente": "producao"` junto com `"debug": True`.
- **Impact:** O debugger do Werkzeug fica exposto em todas as interfaces de rede. Um erro não tratado (por exemplo `POST /admin/query` com body `null`) mostra traceback com código-fonte e o console interativo, protegido só por PIN. Qualquer site consegue chamar a API a partir do navegador.
- **Recommendation:** Ler `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` de variáveis de ambiente, com defaults seguros (debug desligado). (Playbook T-01)

### [HIGH] Broken Authentication — no session/token and missing authorization
- **ID:** AP-06
- **File:** `app.py:14-16`, `app.py:18-19`, `app.py:24-26`, `app.py:28`, `controllers.py:176-180`
- **Description:** `login()` só devolve os dados do usuário com `"mensagem": "Login OK"`, sem emitir token nem sessão, então nenhuma rota consegue saber quem está chamando. Estas operações são públicas: criar, alterar e excluir produto; listar usuários; listar todos os pedidos; ver os pedidos de qualquer usuário (`/pedidos/usuario/<id>`); mudar status de pedido; e o relatório de vendas. A coluna `tipo = 'admin'` nunca é verificada.
- **Impact:** Um cliente anônimo pode mudar preços e o catálogo, aprovar ou cancelar pedidos e ler pedidos e dados pessoais de outros clientes (IDOR).
- **Recommendation:** Adicionar autenticação com token assinado e um guard de papel (`tipo == "admin"`) nas rotas de gestão. Isso é decisão de produto, porque muda o contrato público. (Playbook T-06)

### [HIGH] Business Logic in Routes/Controllers
- **ID:** AP-07
- **File:** `app.py:48-57`, `app.py:60-78`, `controllers.py:188-220`, `controllers.py:237-255`, `controllers.py:264-290`, `models.py:133-169`, `models.py:256-262`
- **Description:**
  - `reset_database()` e `executar_query()` chamam `cursor.execute` dentro da própria rota.
  - `health_check()` roda 4 queries no controller.
  - `criar_pedido()` dispara efeitos colaterais inline (`print("ENVIANDO EMAIL: ...")`, `"ENVIANDO SMS"`, `"ENVIANDO PUSH"`).
  - `atualizar_status_pedido()` escolhe notificações pelo status. Ela imprime `"cancelado. Devolver estoque."`, mas nunca devolve o estoque.
  - O caso de uso de pedido (checar estoque, calcular total, baixar estoque) e as faixas de desconto (`faturamento > 10000` → 10%) ficam misturados ao SQL em `models.py`.
- **Impact:** As regras não podem ser reaproveitadas nem testadas sem HTTP e banco. As notificações ficam presas ao handler, e a mensagem não bate com o que o código realmente faz.
- **Recommendation:** Criar um service de pedidos (criação atômica + notificador injetável). Mover a regra de desconto para uma função ou constantes com nome, deixar só a persistência nos models e deixar os controllers apenas coordenando a chamada. (Playbook T-03, T-13)

### [HIGH] Missing Input Validation — order items
- **ID:** AP-14
- **File:** `controllers.py:195-203`, `models.py:144-146`, `models.py:163-166`
- **Description:** `criar_pedido()` só verifica se `usuario_id` veio preenchido e se `itens` não está vazio. `quantidade` não é validada como inteiro positivo, e ninguém confere se `usuario_id` existe. Com `{"produto_id": 1, "quantidade": -5}`:
  - a checagem `produto["estoque"] < item["quantidade"]` passa;
  - `total` fica negativo;
  - `"UPDATE produtos SET estoque = estoque - " + str(-5)` vira `estoque - -5` e aumenta o estoque.

  Um item sem `produto_id` gera `KeyError` e resposta 500.
- **Impact:** Pedidos com valor negativo distorcem o faturamento em `/relatorios/vendas` e inflam o estoque. Também é possível criar pedidos para usuários que não existem.
- **Recommendation:** Validar cada item (`produto_id` inteiro, `quantidade` inteiro > 0) e a existência do usuário antes de gravar, respondendo 400. (Playbook T-12)

### [HIGH] Mutable Global State
- **ID:** AP-09
- **File:** `database.py:4-11`
- **Description:** `db_connection = None` fica no nível do módulo e é alterado por `global db_connection` dentro de `get_db()`. Uma única conexão `sqlite3.connect(db_path, check_same_thread=False)` é compartilhada por todas as threads do servidor e nunca é fechada, então a transação de uma requisição é a mesma das requisições concorrentes.
- **Impact:** O `db.commit()` de uma requisição confirma escritas pendentes de outra, e uma falha deixa escritas penduradas. Isso gera condições de corrida e torna impossível trocar o banco nos testes.
- **Recommendation:** Abrir uma conexão por requisição (`flask.g` + `teardown_appcontext`) a partir do caminho vindo da configuração. (Playbook T-11, T-18)

### [HIGH] Non-Atomic Multi-Step Writes
- **ID:** AP-11
- **File:** `models.py:139-168`
- **Description:** `criar_pedido()` lê o estoque, compara em Python e depois executa `INSERT INTO pedidos`, N `INSERT INTO itens_pedido` e N `UPDATE produtos SET estoque = estoque - ...`. Não há transação explícita, `rollback()` em caso de erro nem update condicional (`WHERE estoque >= ?`). A checagem é feita item a item: `[{"produto_id": 1, "quantidade": 10}, {"produto_id": 1, "quantidade": 10}]` com estoque 10 passa e deixa `estoque = -10`.
- **Impact:** Venda acima do estoque e estoque negativo; dois pedidos concorrentes passam juntos pela checagem. Se algo falha no meio, as escritas pendentes ficam abertas na conexão compartilhada e acabam confirmadas pela próxima requisição.
- **Recommendation:** Usar transação explícita (`with conn:` para commit/rollback), somar as quantidades por produto e fazer a baixa de estoque condicional, conferindo `rowcount`. (Playbook T-09)

### [MEDIUM] Missing Input Validation — types, null bodies and create/update inconsistency
- **ID:** AP-14
- **File:** `app.py:61-62`, `controllers.py:43-50`, `controllers.py:81-90`, `controllers.py:118-121`, `controllers.py:153-158`, `controllers.py:169-170`, `controllers.py:239-245`
- **Description:**
  - Body `null` ou que não é objeto: `dados.get(...)` gera `AttributeError` e 500 em `executar_query()`, `login()` e `atualizar_status_pedido()`.
  - `preco < 0` e `len(nome)` rodam sem checar tipo: `{"preco": "10"}` gera `TypeError` e 500.
  - `atualizar_produto()` não aplica as validações de tamanho do nome e de categoria que `criar_produto()` faz (linhas 47-54), então aceita categoria fora da lista.
  - `float(preco_min)` em `buscar_produtos()` com `?preco_min=abc` gera `ValueError` e 500.
  - `criar_usuario()` aceita e-mail em qualquer formato e e-mails duplicados.
  - `atualizar_status_pedido()` responde 200 `"Status atualizado"` para um `pedido_id` que não existe.
- **Impact:** Entrada inválida comum vira erro 500 com mensagem interna, e dados inconsistentes entram no banco (categorias inválidas, usuários duplicados que deixam o login ambíguo).
- **Recommendation:** Criar validadores por entidade, reaproveitados no create e no update, respondendo 400 (e 404 quando o recurso não existe). (Playbook T-12)

### [MEDIUM] Swallowed / Generic Exception Handling
- **ID:** AP-15
- **File:** `app.py:77-78`, `controllers.py:10-12`, `controllers.py:21-22`, `controllers.py:60-62`, `controllers.py:95-96`, `controllers.py:108-109`, `controllers.py:125-126`, `controllers.py:133-134`, `controllers.py:143-144`, `controllers.py:164-165`, `controllers.py:185-186`, `controllers.py:218-220`, `controllers.py:226-227`, `controllers.py:234-235`, `controllers.py:254-255`, `controllers.py:261-262`, `controllers.py:291-292`
- **Description:** Cada handler tem seu próprio `except Exception as e: return jsonify({"erro": str(e)}), 500`, que devolve ao cliente o texto cru da exceção (erro do SQLite, `KeyError`). Isso também engole as `HTTPException` do Flask: JSON malformado (400) e content-type errado (415) viram 500. Não existe `@app.errorhandler`, então 404/405 e exceções fora de `try` (por exemplo `app.py:61-62`) respondem com a página HTML do Flask ou com o debugger.
- **Impact:** Detalhes internos vazam (o que ajuda a explorar a SQL injection), erros do cliente aparecem como erros do servidor e o formato das respostas de erro fica inconsistente.
- **Recommendation:** Tirar os try/except dos handlers e registrar tratadores de erro centralizados: `HTTPException` → JSON com o status original, erro de validação → 400, `Exception` → 500 com mensagem genérica e registro em log. (Playbook T-07)

### [MEDIUM] Inadequate Middleware Usage / Inconsistent Responses
- **ID:** AP-19
- **File:** `controllers.py:20`, `controllers.py:70`, `controllers.py:142`, `controllers.py:183`, `controllers.py:206`, `controllers.py:292`
- **Description:** O formato das respostas de erro muda de rota para rota:
  - `{"erro": "Produto não encontrado", "sucesso": False}` em `buscar_produto()`;
  - `{"erro": "Produto não encontrado"}`, sem `sucesso`, em `atualizar_produto()`;
  - `{"erro": "Usuário não encontrado"}` em `buscar_usuario()`;
  - `{"erro": ..., "sucesso": False}` nos erros 401/400 de login e pedidos;
  - `{"status": "erro", "detalhes": ...}` em `health_check()`.

  Tratamento de erro e logging se repetem em cada handler em vez de ficarem num middleware.
- **Impact:** O cliente precisa tratar cada rota de um jeito, e mudar o formato exige editar todos os handlers.
- **Recommendation:** Centralizar a montagem das respostas de erro num middleware, mantendo os campos atuais (`erro`, `sucesso`). (Playbook T-07)

### [MEDIUM] Duplicated Code
- **ID:** AP-16
- **File:** `controllers.py:26-46`, `controllers.py:66-90`, `models.py:12-21`, `models.py:31-40`, `models.py:79-86`, `models.py:95-102`, `models.py:171-201`, `models.py:203-233`, `models.py:304-313`
- **Description:**
  - A cadeia de validação de produto (`"nome" not in dados` ... `preco < 0`) está copiada em `criar_produto()` e `atualizar_produto()`.
  - A conversão de linha de produto em dict aparece 3 vezes (`get_todos_produtos`, `get_produto_por_id`, `buscar_produtos`), e a de usuário 2 vezes.
  - `get_pedidos_usuario()` e `get_todos_pedidos()` são idênticas, exceto por `WHERE usuario_id = ...`.
- **Impact:** Toda correção precisa ser repetida em vários lugares, e as cópias já divergiram (o update não valida categoria).
- **Recommendation:** Um serializer por entidade, um validador compartilhado e uma única função de listagem de pedidos com filtro opcional. (Playbook T-13)

### [MEDIUM] Sensitive Data Exposure — PII in logs
- **ID:** AP-04
- **File:** `controllers.py:161`, `controllers.py:179`, `controllers.py:182`
- **Description:** `print("Usuário criado: " + email)`, `print("Login bem-sucedido: " + email)` e `print("Login falhou: " + email)` escrevem e-mails no stdout, incluindo tentativas de login que falharam.
- **Impact:** Dados pessoais vão para o log sem controle de nível ou retenção (LGPD), e o registro de falhas de login facilita enumerar contas.
- **Recommendation:** Usar um logger com níveis e registrar o id do usuário em vez do e-mail (ou mascará-lo). (Playbook T-05)

### [MEDIUM] N+1 Queries
- **ID:** AP-13
- **File:** `controllers.py:268-274`, `models.py:139-141`, `models.py:154-156`, `models.py:177-200`, `models.py:209-232`, `models.py:239-254`
- **Description:**
  - `get_todos_pedidos()` e `get_pedidos_usuario()` fazem um `SELECT * FROM itens_pedido WHERE pedido_id = ...` por pedido e um `SELECT nome FROM produtos WHERE id = ...` por item (`cursor2`/`cursor3`).
  - `criar_pedido()` busca o mesmo produto duas vezes por item.
  - `relatorio_vendas()` roda 5 agregações separadas (`COUNT(*)`, `SUM(total)` e três `COUNT(*) ... WHERE status = ...`).
  - `health_check()` roda 4 queries.
- **Impact:** `GET /pedidos` com P pedidos e I itens executa 1 + P + I queries, e o tempo de resposta cresce junto com os dados.
- **Recommendation:** Buscar itens e produtos com `JOIN` (ou em lote com `IN (...)`) e agrupar em Python. No relatório, uma única query com `SUM(CASE WHEN status = ? ...)`. (Playbook T-08)

### [MEDIUM] Broken Referential Integrity on Delete
- **ID:** AP-12
- **File:** `database.py:22`, `database.py:45-53`, `models.py:65-70`, `models.py:196`, `models.py:228`
- **Description:** `deletar_produto()` faz `DELETE FROM produtos WHERE id = ...` apagando o registro de vez, mas `itens_pedido.produto_id` não tem `FOREIGN KEY` nem `ON DELETE`. A coluna `ativo`, que serviria para exclusão lógica, nunca é usada. Depois da exclusão, os pedidos antigos passam a mostrar `"produto_nome": "Desconhecido"`. Ficou MEDIUM porque as listagens têm esse fallback e `preco_unitario` preserva os totais.
- **Impact:** O histórico de pedidos perde a referência ao produto, e o banco não garante integridade nenhuma (também aceita `usuario_id`/`produto_id` inexistentes).
- **Recommendation:** Bloquear a exclusão de produtos que têm pedidos, ou usar exclusão lógica via `ativo`. Declarar as chaves estrangeiras no schema. (Playbook T-17)

### [LOW] Magic Numbers and Strings
- **ID:** AP-20
- **File:** `app.py:36`, `app.py:85`, `app.py:88`, `controllers.py:47-50`, `controllers.py:52`, `controllers.py:242`, `controllers.py:285-287`, `database.py:5`, `models.py:150`, `models.py:247-253`, `models.py:257-262`
- **Description:**
  - Faixas de desconto soltas no código: `10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`.
  - Limites de nome `2` e `200`.
  - Lista de categorias e lista de status escritas dentro dos handlers.
  - Status `'pendente'`, `'aprovado'` e `'cancelado'` repetidos no SQL.
  - Versão `"1.0.0"` duplicada em `index()` e `health_check()`.
  - Porta `5000` e `"loja.db"` fixos no código.
- **Impact:** Mudar uma regra ou valor exige caçar literais em vários arquivos, com risco de esquecer algum.
- **Recommendation:** Constantes com nome no domínio (categorias, status, faixas de desconto) e porta/caminho do banco na configuração. (Playbook T-15)

### [LOW] Print Logging Instead of a Logger
- **ID:** AP-23
- **File:** `app.py:56`, `app.py:83-86`, `controllers.py:8`, `controllers.py:11`, `controllers.py:57`, `controllers.py:61`, `controllers.py:106`, `controllers.py:208-210`, `controllers.py:219`, `controllers.py:248`, `controllers.py:250`
- **Description:** `print()` é usado para log operacional e para simular efeitos colaterais (`"ENVIANDO EMAIL: ..."`, `"ENVIANDO SMS: ..."`, `"NOTIFICAÇÃO: ..."`, `"!!! BANCO DE DADOS RESETADO !!!"`), sem níveis nem configuração. Os prints com e-mail (`controllers.py:161`, `controllers.py:179`, `controllers.py:182`) estão no finding de PII acima.
- **Impact:** Não dá para filtrar por nível nem mandar os logs para outro destino, e as "notificações" são só texto no console.
- **Recommendation:** `logging.getLogger(__name__)` configurado no composition root, com as notificações atrás de um service. (Playbook T-16)

### [LOW] Poor Naming
- **ID:** AP-21
- **File:** `controllers.py:14`, `controllers.py:56`, `controllers.py:64`, `controllers.py:98`, `controllers.py:136`, `controllers.py:160`, `models.py:24`, `models.py:54`, `models.py:65`, `models.py:89`, `models.py:187`, `models.py:191`, `models.py:193`, `models.py:219`, `models.py:223`, `models.py:225`
- **Description:** `id` sobrescreve o builtin, tanto como parâmetro quanto como variável (`id = models.criar_produto(...)`, `id = models.criar_usuario(...)`). Nas listagens de pedidos aparecem nomes sem significado: `cursor2`, `cursor3` e `prod`.
- **Impact:** O código fica mais difícil de ler, e o builtin `id()` deixa de estar acessível nessas funções.
- **Recommendation:** Usar `produto_id`, `usuario_id` e nomes descritivos internamente, sem mudar as URLs. (Playbook T-15)

### [LOW] Verbose / Non-idiomatic Conditionals
- **ID:** AP-24
- **File:** `controllers.py:200`
- **Description:** Em `if not itens or len(itens) == 0:`, o `len(itens) == 0` é redundante, porque `not itens` já cobre a lista vazia.
- **Impact:** Ruído na leitura.
- **Recommendation:** `if not itens:`, ou deixar essa checagem para o validador de pedido. (Playbook T-16)

### [LOW] Dead Code and Unused Imports
- **ID:** AP-22
- **File:** `database.py:2`, `models.py:2`, `models.py:63`, `models.py:70`, `models.py:283`
- **Description:** `import os` em `database.py` e `import sqlite3` em `models.py` nunca são usados. `atualizar_produto()`, `deletar_produto()` e `atualizar_status_pedido()` sempre fazem `return True`, e nenhum chamador usa esse valor.
- **Impact:** Ruído e dependências aparentes que não existem de fato.
- **Recommendation:** Remover os imports e os retornos sem uso. (Playbook T-16)

## Deprecated APIs

None detected

```text
================================
Total: 25 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
