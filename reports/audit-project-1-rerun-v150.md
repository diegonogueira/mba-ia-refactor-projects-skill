# Audit Report — code-smells-project (2ª reauditoria pós-avaliação, skill v1.5.0)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.5.0), gerada por `claude -p "/refactor-arch"` dentro de `code-smells-project/`
> (modelo `claude-opus-5-5[1m]`, sessão `21cc7aba-873f-4a13-b7a2-a3c441f690d9`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 2 · HIGH 1 · MEDIUM 1 · LOW 3 · Total 7.

> **Execução descartada.** Esta rodada fechou com 403 listagens e CRUD do domínio (`GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `DELETE /produtos/<id>`…), contrariando o requisito de que os endpoints originais continuem respondendo. A skill foi ajustada (v1.5.1) e a execução que vale está em [`audit-project-1-rerun-v151.md`](audit-project-1-rerun-v151.md).

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.3
Files:   34 analyzed | ~1169 lines of code
```

## Summary

CRITICAL: 2 | HIGH: 1 | MEDIUM: 1 | LOW: 3

## Findings

### [CRITICAL] Unprotected Destructive Endpoints and Missing Authentication
- **ID:** AP-06
- **File:** `src/controllers/usuario_controller.py:32-39`, `src/views/pedido_routes.py:7-14`, `src/views/produto_routes.py:10-12`, `src/views/relatorio_routes.py:7`, `src/views/usuario_routes.py:7-8`
- **Description:** Só `/admin/*` tem guard (`admin_only`). `login()` valida a senha mas não devolve token nem cria sessão (`serializar_login` só tem `id, nome, email, tipo`), então nenhuma rota consegue identificar quem chama. Por isso `DELETE /produtos/<id>`, `POST`/`PUT /produtos`, `PUT /pedidos/<id>/status`, `GET /pedidos`, `GET /usuarios`, `GET /usuarios/<id>` e `GET /relatorios/vendas` são anônimos. O `tipo = 'admin'` existe no banco, mas nenhum código o verifica.
- **Impact:** Qualquer cliente anônimo pode apagar produtos, mudar preço e estoque, aprovar ou cancelar pedidos de outras pessoas, listar e-mails e perfis de todos os usuários, ler todos os pedidos e o faturamento da loja.
- **Recommendation:** Fazer o `/login` emitir um token assinado (`itsdangerous`, já instalado com o Flask) e criar guards `login_required` e `admin_required` (tipo `admin`) em `middlewares/`. Aplicar o guard de admin às escritas de produto, à troca de status e aos relatórios, e o de dono/admin às listagens de pedidos e usuários. Na Phase 3 dá para fechar por padrão, dentro da exceção §9-2, as rotas destrutivas e de dados alheios (`DELETE /produtos/<id>`, `GET /relatorios/vendas`, listagens de usuários e pedidos). Tornar autenticação obrigatória nas demais rotas públicas muda o contrato (200 → 401) e precisa de aprovação. (Playbook T-06)

### [CRITICAL] Sensitive Data Exposure — credential columns readable via /admin/query
- **ID:** AP-04
- **File:** `src/models/sistema_model.py:10-15`, `src/models/sistema_model.py:43-60`
- **Description:** A proteção das colunas de credenciais é uma lista negra por nome. `REFERENCIA_CREDENCIAL` recusa SQL que cite `senha`, e `_sem_credenciais` remove colunas chamadas `senha`. Uma consulta composta renomeia as colunas e passa pelos dois filtros: `SELECT * FROM (VALUES (0,0,0,0,0,0) UNION ALL SELECT * FROM usuarios)` casa com `CONSULTA_SELECT_UNICA` e devolve o hash em `column4`. Testei com o mesmo regex e o mesmo schema num SQLite em memória, e o hash `scrypt:...` voltou. O README.md:68 promete o contrário ("nem `SELECT *` expõe hashes").
- **Impact:** Quem tem o token administrativo, ou um token vazado, extrai os hashes de senha de todos os usuários, inclusive do admin, e pode quebrá-los offline.
- **Recommendation:** Trocar a lista negra por uma lista branca. Opção preferível: remover o SQL livre e expor consultas administrativas pré-definidas. Mínimo aceitável: executar a consulta numa conexão read-only que não enxergue `usuarios.senha` (por exemplo, `sqlite3` `set_authorizer` negando `SQLITE_READ` em `usuarios.senha`). Filtrar pelo nome da coluna do resultado não basta. Corrigir também o README. (Playbook T-05)

### [HIGH] Announced-but-missing Behavior — cancelling an order does not restore stock
- **ID:** AP-07
- **File:** `src/models/pedido_model.py:95-103`, `src/services/notificacao_service.py:18-19`, `src/services/pedido_service.py:12-14`
- **Description:** Ao cancelar, `status_pedido_alterado()` registra `"Pedido %s cancelado. Devolver estoque."`. Mas `pedido_model.atualizar_status()` só executa `UPDATE pedidos SET status = ? WHERE id = ?`: nenhum `UPDATE produtos SET estoque = estoque + ...`. Também não há regra de transição: qualquer status em `STATUS_VALIDOS` pode ir para qualquer outro (`cancelado → aprovado`, `entregue → pendente`).
- **Impact:** O estoque baixado em `criar()` nunca volta quando o pedido é cancelado, e os produtos "somem" do estoque vendável. Um pedido cancelado pode ser reaprovado sem baixa nova, e se a devolução for implementada sem máquina de estados, cancelar duas vezes devolveria o estoque em dobro.
- **Recommendation:** Em `pedido_model.atualizar_status`, usar uma única transação `BEGIN IMMEDIATE` que:
  - lê o status atual;
  - valida a transição contra uma tabela de transições permitidas (`cancelado` e `entregue` terminais → 400);
  - ao passar para `cancelado`, executa `UPDATE produtos SET estoque = estoque + quantidade` a partir de `itens_pedido`.

  O `UPDATE` condicional `WHERE id = ? AND status = <anterior>` garante que a devolução ocorre exatamente uma vez. Manter a notificação só depois do commit. (Playbook T-19, T-09)

### [MEDIUM] Missing Input Validation — unbounded integers crash with 500
- **ID:** AP-14
- **File:** `src/controllers/validators.py:22-23`, `src/controllers/validators.py:46-47`, `src/controllers/validators.py:108`, `src/controllers/validators.py:117-118`, `src/views/pedido_routes.py:10`, `src/views/pedido_routes.py:13`, `src/views/produto_routes.py:9`, `src/views/produto_routes.py:11-12`, `src/views/usuario_routes.py:8`
- **Description:** `_eh_inteiro()` aceita qualquer `int` do Python, sem limite, e os conversores `<int:...>` do Werkzeug também. Um valor acima de 2^63−1 chega ao `sqlite3`, que lança `OverflowError: Python int too large to convert to SQLite INTEGER` (reproduzido em SQLite em memória). Essa exceção não é `AppError` e cai no handler genérico. Exemplos: `GET /produtos/99999999999999999999`, `POST /produtos` com `"estoque": 1e20` inteiro, `POST /pedidos` com `usuario_id` ou `produto_id` enormes.
- **Impact:** Entrada inválida comum devolve HTTP 500 em vez de 400 ou 404, e cada ocorrência gera stack trace no log.
- **Recommendation:** Limitar os inteiros ao intervalo do SQLite (`SQLITE_INT_MAX = 2**63 - 1`) em `_eh_inteiro` e nos limites de estoque e quantidade, respondendo 400. Para parâmetros de rota fora do intervalo, responder 404 (converter `OverflowError` numa `ValidationError`/`NotFoundError` na camada de model ou usar um conversor com `max`). (Playbook T-12)

### [LOW] Dead Configuration — SECRET_KEY never used
- **ID:** AP-22
- **File:** `src/app.py:21`, `src/config/settings.py:31-36`, `src/config/settings.py:60`
- **Description:** `SECRET_KEY` é carregado por `_segredo("SECRET_KEY")` e gravado em `app.config`, mas a aplicação não usa `session`, `flash` nem nada assinado (o grep por `session` não encontra nada).
- **Impact:** Toda subida sem a variável emite o aviso `"SECRET_KEY não definido; usando valor efêmero"` sobre uma chave que não protege nada, o que gera ruído e dá uma falsa sensação de configuração de segurança.
- **Recommendation:** Passar a usá-la de fato como chave do token de login (ver AP-06) ou remover a configuração e o aviso. (Playbook T-16)

### [LOW] Magic Strings — inline config defaults and CORS origin tied to port 5000
- **ID:** AP-20
- **File:** `src/config/settings.py:14`, `src/config/settings.py:62-66`
- **Description:** `CORS_ORIGINS_PADRAO = "http://127.0.0.1:5000"` fixa host e porta, embora `HOST`/`PORT` sejam configuráveis. Além disso, `"127.0.0.1"`, `"5000"`, `"loja.db"` e `"producao"` aparecem inline em `load_settings()`, enquanto outros padrões do mesmo arquivo são constantes nomeadas.
- **Impact:** Com `PORT=8080`, a origem CORS padrão continua apontando para `:5000`. Os valores padrão ficam espalhados e inconsistentes.
- **Recommendation:** Extrair `HOST_PADRAO`, `PORTA_PADRAO`, `BANCO_PADRAO` e `AMBIENTE_PADRAO` e derivar a origem CORS padrão de host e porta efetivos. (Playbook T-15)

### [LOW] Poor Naming — mixed languages for the same concepts
- **ID:** AP-21
- **File:** `src/config/settings.py:17`, `src/config/settings.py:27-40`, `src/config/settings.py:58`, `src/models/database.py:75-109`
- **Description:** O mesmo módulo mistura inglês e português: `configure_logging`/`load_settings` ao lado de `_segredo`/`_lista`/`_bool`; `get_connection`/`transaction`/`close_connection` ao lado de `_senha_do_seed`/`_seed`. O resto do código de domínio está em português (`criar`, `listar`, `conexao`).
- **Impact:** Nomes imprevisíveis dificultam buscar e manter o código. Impacto só de legibilidade.
- **Recommendation:** Adotar um único idioma para identificadores internos (o português do domínio, por exemplo), sem mexer nos campos do contrato HTTP. (Playbook T-15)

## Deprecated APIs

None detected

(Código: nenhuma API da tabela AP-18 aparece. Por exemplo, sem `utcnow`, `before_first_request`, `pkg_resources` ou `__version__`, e sem conversores de datetime do `sqlite3`, já que `detect_types` não é usado. Dependências: a API JSON do PyPI não retornou `vulnerabilities` para `flask==3.1.3`, `flask-cors==6.0.5` e `werkzeug==3.1.8`, e as três já estão na versão mais recente publicada.)

```text
================================
Total: 7 findings
================================
```

**Observação:** o projeto já está em MVC e boa parte das correções anteriores se confirmou na leitura:
- as consultas são parametrizadas;
- as senhas são guardadas com hash;
- o guard administrativo nega acesso por padrão;
- a escrita de pedido é transacional e evita vender acima do estoque;
- o campo `tipo` do cliente é ignorado no cadastro;
- o error handler preserva os headers.

Os achados acima são o que ainda falta. Os mais relevantes são o bypass do `/admin/query`, a devolução de estoque anunciada e não implementada e a ausência de autenticação.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
