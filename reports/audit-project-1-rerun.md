# Audit Report — code-smells-project (auditoria do código já refatorado, após o feedback da avaliação)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.4.0), gerada por `claude -p "/refactor-arch"` dentro de `code-smells-project/`
> (modelo `claude-opus-5[1m]`, sessão `f8bd9da6-7fc3-4b34-b0fc-5cf7fda9cc4e`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 0 · HIGH 1 · MEDIUM 5 · LOW 3 · Total 9.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.3
Files:   34 analyzed | ~1082 lines of code
```

## Summary

CRITICAL: 0 | HIGH: 1 | MEDIUM: 5 | LOW: 3

## Findings

### [HIGH] Sensitive data exposure — credenciais de demonstração semeadas por padrão
- **ID:** AP-04
- **File:** `src/config/settings.py:51`, `src/models/database.py:59-64`, `src/models/database.py:122`
- **Description:** `USUARIOS_SEED` grava contas fixas com senhas públicas — `("Admin", "admin@loja.com", "admin123", "admin")`, `("João Silva", "joao@email.com", "123456", ...)`, `("Maria Santos", "maria@email.com", "senha123", ...)` — e `seed_database=_bool("SEED_DATABASE", True)` deixa a semeadura **ligada por padrão**, inclusive com `APP_ENV` default `"producao"` (`settings.py:50`). As senhas são hasheadas com scrypt (`database.py:113`), mas os valores em texto puro estão no repositório.
- **Impact:** Qualquer cliente anônimo autentica em `POST /login` com `admin@loja.com`/`admin123` e recebe `{"id": 1, "tipo": "admin"}` (`src/views/serializers.py:4`). Hoje o `tipo` não concede autorização em nenhuma rota (os endpoints `/admin/*` usam token próprio), então o ganho imediato é o acesso à identidade "admin" e a confirmação de contas válidas; num deploy real que passe a usar `tipo` para autorização, isso vira escalação de privilégio direta.
- **Recommendation:** Inverter o padrão de `SEED_DATABASE` para `False` (opt-in explícito de demonstração) e/ou gerar a senha do seed a partir de variável de ambiente, abortando a criação da conta `admin` quando ela não for fornecida. (Playbook T-05)

### [MEDIUM] Insecure runtime configuration — CORS liberado para qualquer origem por padrão
- **ID:** AP-10
- **File:** `src/app.py:28`, `src/config/settings.py:49`
- **Description:** `cors_origins=_lista("CORS_ORIGINS", "*")` define `*` como padrão e `CORS(app, origins=settings.cors_origins)` aplica esse valor sem restrição. Subir a aplicação sem definir `CORS_ORIGINS` libera todas as origens.
- **Impact:** Qualquer página web pode chamar a API a partir do navegador da vítima e ler as respostas, incluindo `GET /usuarios` (lista de e-mails) e `GET /relatorios/vendas` (faturamento). Como as rotas são públicas, o impacto é de exposição de dados, não de CSRF autenticado.
- **Recommendation:** Trocar o padrão para uma lista fechada (ex.: `http://127.0.0.1:5000`) e exigir `CORS_ORIGINS` explícito para liberar outras origens; documentar `*` apenas como opção de desenvolvimento. (Playbook T-01)

### [MEDIUM] Non-atomic multi-step writes — verificação de existência fora da transação de escrita
- **ID:** AP-11
- **File:** `src/controllers/produto_controller.py:15-19`, `src/controllers/produto_controller.py:48-52`, `src/controllers/produto_controller.py:55-58`, `src/models/produto_model.py:65-71`
- **Description:** `atualizar_produto` e `deletar_produto` chamam `_obter_produto(produto_id)` — um `SELECT` isolado — e só depois entram em `produto_model.atualizar()`/`deletar()`, que abrem a transação. `atualizar()` executa o `UPDATE` sem checar `rowcount`, diferente de `pedido_model.atualizar_status`, que valida `alterados == 0` e levanta `NotFoundError` (`src/models/pedido_model.py:99-103`).
- **Impact:** Em concorrência (duas requisições no mesmo produto), o `UPDATE` pode afetar 0 linhas depois de o registro ter sido removido e ainda assim a API responde `200 {"mensagem": "Produto atualizado"}` — o cliente recebe confirmação de uma escrita que não aconteceu. `deletar()` tem o mesmo comportamento com `200 "Produto deletado"`.
- **Recommendation:** Mover a checagem para dentro da transação: em `produto_model.atualizar()`/`deletar()` usar o `rowcount` do próprio `UPDATE`/`DELETE` e levantar `NotFoundError` quando for 0, como já faz `pedido_model.atualizar_status`. (Playbook T-09)

### [MEDIUM] Inadequate middleware usage — handler central recria a resposta e descarta headers do framework
- **ID:** AP-19
- **File:** `src/middlewares/error_handler.py:20-21`, `src/middlewares/error_handler.py:29-31`, `src/controllers/sistema_controller.py:26-31`
- **Description:** `tratar_erro_http` devolve `jsonify({"erro": ..., "sucesso": False}), erro.code`, ou seja, uma resposta nova, ignorando `erro.get_response()`. Todos os headers que a `HTTPException` do Werkzeug carrega são perdidos. Em paralelo, `health_check` monta seu próprio erro `{"status": "erro", "detalhes": "Banco de dados indisponível"}` com status 500, um envelope diferente do `{"erro": ..., "sucesso": false}` usado em todo o resto da API.
- **Impact:** Um `405 Method Not Allowed` (ex.: `DELETE /produtos`) responde sem o header `Allow`, que é obrigatório pela RFC 9110 §15.5.6 — clientes e proxies perdem a informação de quais métodos a rota aceita; o mesmo vale para `WWW-Authenticate` e `Retry-After` se forem usados no futuro. A divergência do `/health` quebra a uniformidade de tratamento de erro para os consumidores.
- **Recommendation:** Em `tratar_erro_http`, partir de `resposta = erro.get_response()`, substituir apenas o corpo pelo JSON do envelope e preservar `resposta.headers` (copiando `Allow` e demais headers); fazer `health_check` levantar um `AppError` (ou usar `_resposta_erro`) em vez de montar um envelope próprio. (Playbook T-07)

### [MEDIUM] Missing or inconsistent input validation — cadastro de usuário sem política de senha nem limites de tamanho
- **ID:** AP-14
- **File:** `src/controllers/validators.py:68-78`, `src/controllers/validators.py:81-86`
- **Description:** `ler_usuario` só exige que `nome`, `email` e `senha` sejam strings não vazias e que o e-mail case com `EMAIL_FORMATO`. Não há comprimento mínimo de senha nem máximo para nenhum dos três campos — `{"nome": "a", "email": "a@b.c", "senha": "1"}` é aceito. A validação de produto, no mesmo domínio, é bem mais rígida (`NOME_TAMANHO_MINIMO = 2`, `NOME_TAMANHO_MAXIMO = 200` em `src/models/produto_model.py:7-8`, aplicados em `validar()`), o que caracteriza validação inconsistente entre entidades.
- **Impact:** Contas com senha de um caractere passam pelo cadastro e ficam sujeitas a força bruta trivial (não há rate limiting em `POST /login`); campos sem teto permitem gravar `nome`/`email` de tamanho arbitrário no SQLite, inchando as respostas de `GET /usuarios` e o banco.
- **Recommendation:** Criar constantes de política no validador (mínimo de 8 caracteres para `senha`, máximos para `nome`/`email` alinhados aos de produto) e aplicá-las em `ler_usuario`, retornando `ValidationError` (400) — sem alterar os nomes de campo do contrato. (Playbook T-12)

### [MEDIUM] Sensitive data exposure — `/admin/query` consegue ler a coluna de senhas
- **ID:** AP-04
- **File:** `src/models/sistema_model.py:10`, `src/models/sistema_model.py:38-49`, `src/views/sistema_routes.py:11`
- **Description:** `consultar_somente_leitura` valida a entrada apenas com `CONSULTA_SELECT_UNICA = re.compile(r"^\s*select\b[^;]*;?\s*$")` e executa a consulta numa conexão `mode=ro` + `PRAGMA query_only = ON`. A restrição é só de escrita: não há allowlist de tabelas nem de colunas, então `{"sql": "SELECT email, senha FROM usuarios"}` retorna os hashes scrypt de todos os usuários.
- **Impact:** Exfiltração offline dos hashes de senha (e de qualquer outro dado do banco) por quem tenha o `X-Admin-Token`. Mitigado por `ADMIN_ENDPOINTS_ENABLED=false` por padrão (`src/config/settings.py:52`) e pelo guard com `hmac.compare_digest` (`src/middlewares/admin_guard.py:18-20`) — por isso MEDIUM e não CRITICAL — mas um vazamento do token vira vazamento de credenciais.
- **Recommendation:** Filtrar as colunas sensíveis no próprio model: rejeitar a consulta quando ela referenciar `senha` (ou aplicar uma allowlist de tabelas/colunas consultáveis) e mascarar o valor nas linhas retornadas. (Playbook T-05)

### [LOW] print/console logging instead of a logger — logging configurado só no caminho `python app.py`
- **ID:** AP-23
- **File:** `app.py:11`, `src/app.py:15-34`
- **Description:** `logging.basicConfig(level=logging.INFO, ...)` está dentro de `main()` em `app.py`. Todos os módulos usam `logging.getLogger(__name__)` corretamente, mas `create_app()` não configura handler nem nível algum.
- **Impact:** Ao servir a aplicação por um WSGI server que importa a factory (`gunicorn "src.app:create_app()"`), nenhum dos `logger.info`/`logger.warning` da aplicação é emitido — inclusive `logger.warning("Banco de dados resetado via /admin/reset-db")` (`src/controllers/sistema_controller.py:43`), que é trilha de auditoria.
- **Recommendation:** Mover a configuração de logging para `create_app()` (ou para um `configure_logging(settings)` chamado por ela), mantendo `app.py` apenas como wrapper do `app.run()`. (Playbook T-16)

### [LOW] Duplicated code — tabela de rotas replicada no handler do índice
- **ID:** AP-16
- **File:** `src/controllers/sistema_controller.py:12-19`
- **Description:** `ENDPOINTS_PUBLICOS` repete literalmente os caminhos já declarados nos blueprints (`"/produtos"`, `"/usuarios"`, `"/pedidos"`, `"/login"`, `"/relatorios/vendas"`, `"/health"`), duplicando a fonte da verdade que vive em `src/views/*_routes.py`.
- **Impact:** Qualquer mudança de path nos blueprints deixa `GET /` anunciando rotas erradas, sem nenhum teste ou checagem que detecte a divergência.
- **Recommendation:** Derivar a lista de `current_app.url_map` (filtrando os prefixos internos e `/admin`) ou, se o conteúdo estático for parte do contrato, mover as constantes para o módulo de views que já declara as rotas. (Playbook T-13)

### [LOW] Dead code — coluna `ativo` nunca escrita nem filtrada
- **ID:** AP-22
- **File:** `src/models/database.py:19`, `src/models/produto_model.py:10`, `src/views/serializers.py:2`
- **Description:** A coluna `ativo INTEGER DEFAULT 1` existe no schema e é selecionada (`COLUNAS`) e serializada (`CAMPOS_PRODUTO`), mas nenhum `INSERT`/`UPDATE` a define e nenhuma consulta filtra por ela — `produto_model.criar`, `atualizar` e `buscar` a ignoram por completo.
- **Impact:** O campo `ativo` aparece no contrato de todos os endpoints de produto sempre com valor `1`, sugerindo um soft delete que não existe; quem consumir a API pode assumir que produtos inativos são filtrados quando não são.
- **Recommendation:** Decidir e implementar uma das duas opções — usar a coluna (soft delete em `deletar` e filtro em `listar_todos`/`buscar`) ou removê-la do schema e do serializer. Remover do serializer altera o contrato de resposta, então prefira implementar o soft delete. (Playbook T-16)

## Deprecated APIs

None detected — nenhuma API depreciada do catálogo (AP-18) aparece no código (`utcnow`, `before_first_request`, `JSONEncoder`, `flask.__version__`, `_app_ctx_stack`, `werkzeug.urls`, `distutils`, `pkg_resources`, `FLASK_ENV`/`app.env` retornaram zero ocorrências) e a auditoria de dependências na API JSON do PyPI devolveu `vulnerabilities: []` para `flask==3.1.3`, `flask-cors==6.0.5` e `werkzeug==3.1.8` — as três pinadas na versão mais recente publicada.

```text
================================
Total: 9 findings
================================
```

O relatório mostra a árvore limpa (nenhuma alteração não commitada), então não é necessário backup antes de prosseguir.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
