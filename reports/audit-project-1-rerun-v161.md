# Audit Report — code-smells-project (reauditoria final, skill v1.6.1)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.6.1), gerada por `claude -p "/refactor-arch"` dentro de `code-smells-project/`
> (modelo `claude-opus-5-5`, Claude Code 2.1.282, sessão `ef2691b5-8d95-4728-80d1-ec11a8170b1e`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 0 · HIGH 1 · MEDIUM 0 · LOW 3 · Total 4.
> Esta execução produziu o código versionado do projeto. Ela audita o código já refatorado, por isso sobram poucos findings; o relatório do código legado é o [`audit-project-1.md`](audit-project-1.md).

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.3
Files:   38 analyzed | ~1349 lines of code
```

## Summary

CRITICAL: 0 | HIGH: 1 | MEDIUM: 0 | LOW: 3

## Findings

### [HIGH] Broken Authentication — pedido criado em nome de qualquer usuário
- **ID:** AP-06
- **File:** `src/views/pedido_routes.py:8`, `src/controllers/pedido_controller.py:9-12`, `src/controllers/validators.py:116-123`, `src/models/pedido_model.py:56-73`, `README.md:50`
- **Description:** `POST /pedidos` está registrado sem guard (`pedido_bp.add_url_rule("/pedidos", "criar_pedido", controller.criar_pedido, ...)`). O `usuario_id` vem do corpo (`dados.get("usuario_id")` em `ler_pedido()`), e o model só confere se o usuário existe (`SELECT 1 FROM usuarios WHERE id = ?`) antes de gravar o pedido e baixar o estoque (`UPDATE produtos SET estoque = estoque - ? ...`). Nada liga o chamador ao `usuario_id`, embora o `/login` já emita um token assinado. O README (linha 50) documenta a rota como pública.
- **Impact:** Um cliente anônimo cria pedidos em nome de qualquer usuário (IDOR): os pedidos aparecem no histórico da vítima (`GET /pedidos/usuario/<id>`) e no faturamento do `GET /relatorios/vendas`. Além disso, cada pedido reserva estoque sem limite. Com um laço de requisições é possível zerar o estoque do catálogo e bloquear as vendas legítimas, porque os pedidos ficam `pendente` até um administrador cancelá-los um a um.
- **Recommendation:** Exigir `Authorization: Bearer <token>` no `POST /pedidos`, reaproveitando o `_usuario_autenticado()` de `src/middlewares/auth_guard.py`. Sem token ou com token adulterado/expirado, responder 401. Se o `usuario_id` do corpo for diferente do usuário do token e o chamador não for admin, responder 403. Com token do próprio usuário, a resposta 201 e o envelope continuam iguais. Atualizar a tabela de acesso do README e registrar a mudança em "Contract Changes" (mvc-guidelines §9, exceção 11, "Acting on behalf of a user"). (Playbook T-06)

### [LOW] Poor Naming
- **ID:** AP-21
- **File:** `src/controllers/sistema_controller.py:14-21`
- **Description:** O dicionário `ENDPOINTS_PUBLICOS`, usado no índice `GET /`, inclui `usuarios.listar_usuarios`, `pedidos.listar_todos_pedidos` e `relatorios.relatorio_vendas`, que exigem papel `admin` (`admin_required`).
- **Impact:** O nome induz quem mantém o código a achar que essas rotas são públicas. Isso pode levar a remover um guard por engano ou a documentar o acesso errado.
- **Recommendation:** Renomear internamente para `ENDPOINTS_INDICE` (ou equivalente). O conteúdo da resposta do `GET /` fica igual. (Playbook T-15)

### [LOW] Magic Strings
- **ID:** AP-20
- **File:** `src/models/database.py:42`
- **Description:** O schema fixa `status TEXT DEFAULT 'pendente'` como literal, repetindo `STATUS_PENDENTE` (`src/models/pedido_model.py:5`). O default de `tipo` na linha 36 usa a constante `TIPO_CLIENTE` via `tipos_usuario.py`.
- **Impact:** Se o nome do status mudar, o default do banco e a regra de pedidos deixam de coincidir sem nenhum erro. O padrão também fica inconsistente dentro do mesmo schema.
- **Recommendation:** Levar os status de pedido para um módulo próprio (como `tipos_usuario.py`, sem import circular) e interpolar a constante no schema. (Playbook T-15)

### [LOW] Dead Code and Redundant Calls
- **ID:** AP-22
- **File:** `src/middlewares/auth_guard.py:29`, `app.py:11`
- **Description:** `_usuario_autenticado()` grava `g.usuario = usuario`, mas `g.usuario` não é lido em nenhum lugar do código (grep só encontra essa atribuição). `main()` chama `configure_logging()` antes de `create_app(settings)`, e `create_app()` já faz a mesma chamada (`src/app.py:17`).
- **Impact:** Um estado aparentemente disponível para os controllers, mas não usado, e uma chamada duplicada tornam a leitura mais difícil sem ganho nenhum.
- **Recommendation:** Remover a atribuição a `g.usuario`, ou fazer os controllers usá-la quando precisarem do usuário autenticado (por exemplo, na correção do AP-06 acima). Remover a chamada redundante de `app.py`. (Playbook T-16)

## Deprecated APIs

None detected

Detalhes das duas verificações:
- **Código:** grep das APIs da tabela AP-18 (`utcnow`, `before_first_request`, `.query.get`, `flask.__version__`, conversores de data do sqlite3, `distutils`/`imp`/`pkg_resources`). Nenhuma ocorrência.
- **Dependências:** consulta à API JSON do PyPI para `flask==3.1.3`, `flask-cors==6.0.5`, `itsdangerous==2.2.0` e `werkzeug==3.1.8`. O array `vulnerabilities` veio vazio para as quatro, e todas estão na versão mais recente publicada.
- **Observação de reprodutibilidade:** as dependências transitivas (jinja2, click, blinker, markupsafe) não estão fixadas no `requirements.txt`.

```text
================================
Total: 4 findings
================================
```

O projeto já está em MVC. Dois pontos do catálogo foram analisados e descartados, porque o `mvc-guidelines.md` §9 aceita explicitamente o padrão usado:
- **Senha do seed registrada uma única vez no log** (`src/models/database.py:119-123`): corresponde à exceção 8.
- **Migração de senha legada em texto puro no primeiro login** (`src/models/usuario_model.py:51-55`): corresponde à exceção 7.

Há alterações não commitadas nos arquivos da skill (`SKILL.md`, `mvc-guidelines.md`). Recomendo fazer commit ou backup antes da Fase 3.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
