# Audit Report — code-smells-project (2ª reauditoria pós-avaliação, skill v1.5.1)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.5.1), gerada por `claude -p "/refactor-arch"` dentro de `code-smells-project/`
> (modelo `claude-opus-5-5[1m]`, sessão `162126e3-47e8-46d2-9908-12d32db4445b`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 2 · HIGH 1 · MEDIUM 1 · LOW 1 · Total 5.
> Esta é a execução que vale para o código versionado. A anterior, com a v1.5.0 ([`audit-project-1-rerun-v150.md`](audit-project-1-rerun-v150.md)), foi descartada: fechou listagens do domínio com 403.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.3
Files:   34 analyzed | ~1170 lines of code
```

## Summary

CRITICAL: 2 | HIGH: 1 | MEDIUM: 1 | LOW: 1

## Findings

### [CRITICAL] Sensitive Data Exposure — bypass do filtro de credenciais em /admin/query
- **ID:** AP-04
- **File:** `src/models/sistema_model.py:10-15`, `src/models/sistema_model.py:43-60`
- **Description:** `consultar_somente_leitura()` protege as credenciais de duas formas: recusa o SQL que contém a palavra `senha`/`password`/`token`/`secret` (`REFERENCIA_CREDENCIAL`) e remove das linhas as colunas com esses nomes (`_sem_credenciais`). Só que o nome de uma coluna num `UNION` vem do primeiro `SELECT`. `SELECT 1,2,3,4,5,6 UNION ALL SELECT * FROM usuarios` passa pela regex `CONSULTA_SELECT_UNICA`, não cita nenhuma palavra bloqueada e devolve o hash na coluna `"4"`. Testei isso num SQLite em memória com o mesmo schema e as mesmas regex.
- **Impact:** Quem tem o token de admin consegue ler os hashes de senha de todos os usuários (e fazer quebra offline), mesmo com o controle explícito que diz que "nem `SELECT *` expõe hashes de senha" (README). A garantia anunciada não se cumpre.
- **Recommendation:** Trocar o filtro por texto e nome de coluna por um bloqueio no próprio SQLite. Registrar `conexao.set_authorizer()` na conexão somente leitura, retornando `SQLITE_IGNORE` para `SQLITE_READ` nas colunas de credenciais (a coluna passa a vir `NULL`, qualquer que seja o alias ou `UNION`) e `SQLITE_DENY` para tudo que não for leitura. A recusa por texto continua como defesa extra. Validar com a própria carga de `UNION`. (Playbook T-05)

### [CRITICAL] Unprotected Endpoints and Broken Authentication — rotas de domínio sem autenticação
- **ID:** AP-06
- **File:** `src/views/pedido_routes.py:8`, `src/views/pedido_routes.py:12-14`, `src/views/produto_routes.py:10-12`, `src/views/relatorio_routes.py:7`, `src/views/usuario_routes.py:7-8`, `src/controllers/usuario_controller.py:32-39`
- **Description:** `POST /login` confere a senha, mas não emite token nem sessão (`serializar_login` devolve só `id, nome, email, tipo`). Por isso nenhuma rota consegue identificar quem chama. Qualquer cliente anônimo pode apagar e alterar produtos e preços (`DELETE`/`PUT /produtos/<id>`), mudar o status de qualquer pedido (`PUT /pedidos/<id>/status`), listar os pedidos de todos (`GET /pedidos`), ver o faturamento (`GET /relatorios/vendas`) e listar nome e e-mail de todos os usuários (`GET /usuarios`, `/usuarios/<id>`).
- **Impact:** Um anônimo, sem nenhuma credencial, consegue destruir e alterar dados do catálogo, cancelar ou "entregar" pedidos alheios e extrair PII (e-mails) e números financeiros. O campo `tipo='admin'` não tem nenhum efeito.
- **Recommendation:** Fazer o login emitir um token assinado (`itsdangerous`, que já vem com o Flask) e criar guards em `middlewares/`: admin para escrita no catálogo, status de pedido, relatório e listagem de usuários, e dono ou admin para os pedidos de um usuário. Isso transforma um 200 legítimo em 401/403, o que é quebra de contrato (mvc-guidelines §9, "Not allowed without asking the user"). Sem autorização explícita sua, fica em "Remaining Items". A parte que não depende de autenticação já está correta: `tipo` não é aceito do cliente (`src/models/usuario_model.py:33`). (Playbook T-06)

### [HIGH] Business Logic — cancelamento anuncia devolução de estoque que não acontece
- **ID:** AP-07
- **File:** `src/models/pedido_model.py:95-103`, `src/services/notificacao_service.py:15-19`, `src/services/pedido_service.py:12-14`
- **Description:** Com `novo_status == "cancelado"`, `notificacao_service.status_pedido_alterado()` registra `"Pedido %s cancelado. Devolver estoque."`, mas `pedido_model.atualizar_status()` só executa `UPDATE pedidos SET status = ? WHERE id = ?`. Nenhuma escrita devolve as quantidades de `itens_pedido` para `produtos.estoque`. Também não há regra de transição: um pedido cancelado pode voltar a `aprovado`, e cancelar duas vezes gera a notificação duas vezes.
- **Impact:** Correção: a regra "cancelar devolve o estoque" é anunciada mas não implementada. O estoque baixado em `criar()` (`src/models/pedido_model.py:59-62`) nunca volta, e os produtos ficam indisponíveis para venda. Pedidos cancelados podem ser reativados sem baixar o estoque de novo.
- **Recommendation:** Em `pedido_model.atualizar_status()`, dentro de `transaction(immediate=True)`: ler o status atual (404 se o pedido não existir), tratar `cancelado` e `entregue` como estados finais (sair deles → 400) e aplicar a mudança com compare-and-set (`UPDATE ... WHERE id = ? AND status = ?`). Na transição para `cancelado`, somar de volta a `produtos.estoque` as quantidades de `itens_pedido` na mesma transação, exatamente uma vez. Repetir o mesmo status deve ser no-op e não disparar notificação. O `pedido_service` só notifica quando o status realmente mudou. (Playbook T-19, T-09)

### [MEDIUM] Missing Input Validation — inteiros fora da faixa do SQLite causam 500
- **ID:** AP-14
- **File:** `src/controllers/validators.py:18-23`, `src/views/produto_routes.py:9`, `src/views/produto_routes.py:11-12`, `src/views/usuario_routes.py:8`, `src/views/pedido_routes.py:10`, `src/views/pedido_routes.py:13`
- **Description:** `_eh_numero()` e `_eh_inteiro()` checam só o tipo, sem faixa, e o conversor `<int:...>` do Werkzeug aceita qualquer tamanho. Valores ≥ 2^63 chegam ao `sqlite3`, que lança `OverflowError: Python int too large to convert to SQLite INTEGER`. Como esse erro não é `sqlite3.Error`, cai no handler genérico e vira 500. Com `preco: 10**400`, o próprio `math.isfinite()` lança `OverflowError` dentro do validador. Exemplos: `GET /produtos/99999999999999999999`, `POST /produtos` com `"estoque": 9223372036854775808`, `POST /pedidos` com `produto_id` gigante.
- **Impact:** Uma entrada inválida comum derruba a requisição com HTTP 500 (e um stack trace no log), em vez de 400/404.
- **Recommendation:** Limitar os inteiros aceitos à faixa de 64 bits com sinal nos validadores (400 com mensagem) e registrar um conversor de URL `int` com teto (id acima do máximo → 404, como um id inexistente). Em `_eh_numero`, rejeitar inteiros que não convertem para `float`. (Playbook T-12)

### [LOW] Magic Strings — padrões de host/porta duplicados no CORS
- **ID:** AP-20
- **File:** `src/config/settings.py:14`, `src/config/settings.py:62-63`
- **Description:** `CORS_ORIGINS_PADRAO = "http://127.0.0.1:5000"` repete, como literal, os padrões `"127.0.0.1"` e `"5000"` que `load_settings()` também escreve inline, sem nome.
- **Impact:** Com `PORT=8080` (ou outro `HOST`), a origem liberada por padrão continua sendo `http://127.0.0.1:5000`. Isso concede acesso cross-origin a outra aplicação local nessa porta e não à própria API. As duas fontes do mesmo valor podem divergir.
- **Recommendation:** Criar as constantes `HOST_PADRAO`/`PORTA_PADRAO` e derivar a origem padrão do host e da porta efetivos (`f"http://{host}:{port}"`) quando `CORS_ORIGINS` não estiver definido. (Playbook T-15)

## Deprecated APIs

None detected

(Código: nenhuma API da tabela AP-18 aparece. O `sqlite3` não usa `detect_types`, então os adapters depreciados no 3.12 não são usados. Dependências: a API JSON do PyPI respondeu `vulnerabilities: []` para flask 3.1.3, flask-cors 6.0.5 e werkzeug 3.1.8, e as três são as versões mais recentes publicadas.)

```text
================================
Total: 5 findings
================================
```

Sobre o AP-06: fechar as rotas de domínio exige autenticação obrigatória, que é uma mudança de contrato. Se você quiser isso, responda por exemplo `sim, incluindo autenticação`. Com só `sim`, esse item fica em "Remaining Items" e a validação final vai mostrar ✗.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
