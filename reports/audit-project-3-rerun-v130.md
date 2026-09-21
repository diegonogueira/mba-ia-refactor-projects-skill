# Audit Report — task-manager-api (auditoria do código refatorado logo após o feedback da avaliação)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.3.0), gerada por `claude -p "/refactor-arch"` dentro de `task-manager-api/`
> (modelo `claude-opus-5[1m]`, sessão `65a64028-00eb-4add-bf9d-5333e204e1a0`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 1 · HIGH 1 · MEDIUM 4 · LOW 2 · Total 8.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.1.3
Files:   39 analyzed | ~1536 lines of code
```

## Summary

CRITICAL: 1 | HIGH: 1 | MEDIUM: 4 | LOW: 2

## Findings

### [CRITICAL] Unprotected Destructive Endpoints — nenhuma autenticação aplicada
- **ID:** AP-06
- **File:** `src/views/user_routes.py:7-14`, `src/views/task_routes.py:7-13`, `src/views/category_routes.py:7-12`, `src/views/report_routes.py:7-8`, `src/services/auth_service.py:33-34`
- **Description:** As 22 rotas são registradas com `add_url_rule` sem nenhum guard: não existe `before_request`, decorator de autenticação nem leitura do header `Authorization` em lugar algum (grep por `Authorization`, `before_request`, `loads(` não retorna ocorrências fora dos docstrings). `AuthService.issue_token()` emite um token assinado com `URLSafeTimedSerializer`, mas nenhum módulo chama `.loads()` para verificá-lo — o token é decorativo. Assim, `DELETE /users/<id>` (que apaga em cascata as tasks do usuário, `src/models/user_model.py:33`), `DELETE /tasks/<id>`, `DELETE /categories/<id>` e todos os `PUT` são executáveis por qualquer cliente anônimo.
- **Impact:** Qualquer pessoa com acesso de rede à API destrói dados de forma irreversível (um `DELETE /users/1` remove o usuário e todas as tasks dele) e lê a base inteira de usuários, incluindo e-mails e o campo `role`.
- **Recommendation:** Introduzir um middleware/guard que valide o token assinado emitido no `/login` (com expiração via `max_age`) e exigir papel adequado nas rotas de escrita e nas administrativas de usuários. (Playbook T-06)

### [HIGH] Privilege Escalation — `role` aceito do corpo da requisição
- **ID:** AP-06
- **File:** `src/controllers/validators/user_validator.py:54`, `src/controllers/validators/user_validator.py:68`, `src/controllers/validators/user_validator.py:86-87`
- **Description:** `validate_new_user()` lê `role = data.get('role', DEFAULT_ROLE)` e devolve `'role': _role(role)`, que o controller repassa a `User.register(**fields)` (`src/controllers/user_controller.py:36`). `_role()` só confere se o valor está em `USER_ROLES = ('user', 'admin', 'manager')` — ou seja, aceita `admin`. `validate_user_changes()` repete o mesmo em `if 'role' in data: changes['role'] = _role(data['role'])`, permitindo promover qualquer usuário existente via `PUT /users/<id>`.
- **Impact:** Um cliente anônimo se auto-cadastra como `admin` (`POST /users` com `{"role": "admin"}`) ou promove/rebaixa qualquer conta, anulando qualquer controle de autorização que venha a ser adicionado depois. O campo `active` tem o mesmo problema (`:88-89`): dá para desativar contas alheias e negar o login delas.
- **Recommendation:** Remover `role` e `active` do conjunto de campos aceitos de clientes não autenticados: criar sempre com `DEFAULT_ROLE` e só permitir alteração desses campos através de uma rota/guard administrativo. (Playbook T-06)

### [MEDIUM] Insecure Password Storage — política fraca e verificação MD5 legada
- **ID:** AP-05
- **File:** `src/models/user_model.py:14`, `src/models/user_model.py:16`, `src/models/user_model.py:40-48`
- **Description:** O armazenamento em si está correto (`generate_password_hash` do Werkzeug, `:38`), mas `MIN_PASSWORD_LENGTH = 4` permite senhas de 4 caracteres, e `check_password()` mantém um ramo alternativo que compara `hashlib.md5(raw_password.encode()).hexdigest()` quando o hash gravado casa com `LEGACY_MD5_PATTERN = ^[0-9a-f]{32}$`. Esse ramo é hoje código morto: não existe diretório `instance/` no repositório e `src/models/seed.py:62` grava apenas hashes Werkzeug, de modo que nenhuma linha em base pode ter formato MD5.
- **Impact:** Senhas de 4 caracteres são quebráveis por força bruta em segundos, ainda mais com `/login` sem rate limiting. O caminho MD5 mantém uma rotina de verificação fraca viva no código de autenticação, pronta para aceitar hashes MD5 caso qualquer base antiga ou script volte a gravá-los.
- **Recommendation:** Elevar o mínimo de senha para 8 caracteres e remover o ramo MD5 junto com `has_legacy_hash()`/`LEGACY_MD5_PATTERN`, deixando `check_password()` com uma única implementação baseada em `check_password_hash`. (Playbook T-04)

### [MEDIUM] Insecure Runtime Configuration — CORS liberado para qualquer origem por padrão
- **ID:** AP-10
- **File:** `src/config/settings.py:17`, `src/config/settings.py:48-52`, `src/app.py:38`, `.env.example:17`
- **Description:** `DEFAULT_CORS_ORIGINS = '*'` é o default de `load_settings()`; `_cors_origins()` devolve explicitamente `'*'` quando a variável está vazia ou é `*`, e `CORS(app, origins=settings.cors_origins)` aplica isso à aplicação inteira. O `.env.example` distribuído também traz `CORS_ORIGINS=*`, então a configuração "de partida" documentada é a permissiva.
- **Impact:** Qualquer página web consegue chamar todos os endpoints a partir do navegador da vítima, incluindo os destrutivos descritos em AP-06 — o wildcard transforma a ausência de autenticação em um vetor CSRF a partir de qualquer site.
- **Recommendation:** Trocar o default para uma lista explícita de origens de desenvolvimento (ex.: `http://localhost:3000`) e manter `*` apenas como opt-in consciente via variável de ambiente. (Playbook T-01)

### [MEDIUM] N+1 / Per-Row Aggregation — relatório por usuário agrega em memória
- **ID:** AP-13
- **File:** `src/services/report_service.py:56-68`
- **Description:** `user_report()` chama `Task.list_by_user(user_id)` para carregar todas as linhas do usuário e depois calcula tudo em Python: laço `for task in tasks: by_status[task.status] += 1`, `sum(1 for task in tasks if task.is_overdue(now))` e `sum(1 for task in tasks if task.is_high_priority())`. O modelo já expõe as agregações equivalentes no banco (`Task.count_by_status`, `Task.count_overdue`, e `is_overdue` tem expressão SQL em `src/models/task_model.py:60-64`), usadas corretamente por `task_statistics()` (`:19-25`).
- **Impact:** `GET /reports/user/<id>` transfere e instancia todas as tasks do usuário para produzir seis números; o custo de memória e tempo cresce linearmente com o histórico, enquanto o relatório global equivalente é O(1) em linhas trazidas.
- **Recommendation:** Adicionar consultas agregadas por usuário no `Task` (`GROUP BY status` filtrado por `user_id`, `count` de vencidas e de alta prioridade) e consumi-las no service, como já é feito em `task_statistics()`. (Playbook T-08)

### [MEDIUM] Missing or Inconsistent Input Validation — limites do schema não são checados
- **ID:** AP-14
- **File:** `src/controllers/validators/category_validator.py:20-31`, `src/controllers/validators/user_validator.py:30-33`, `src/controllers/validators/user_validator.py:19`, `src/controllers/validators/user_validator.py:42-45`
- **Description:** Três lacunas com a mesma raiz — os validadores não refletem as restrições declaradas nos modelos:
  - `validate_new_category()` aplica só `ensure_optional_text` a `color` e `description`, sem verificar formato nem tamanho, embora a coluna seja `db.String(COLOR_LENGTH)` com `COLOR_LENGTH = 7` (`src/models/category_model.py:8,19`); `name` também passa sem limite contra `db.String(100)`.
  - `_name()` em usuários (`:30-33`) e o `email` (`:68`) seguem sem checagem de comprimento contra `db.String(100)` e `db.String(150)`.
  - `_active()` testa `value not in ACTIVE_VALUES` com `ACTIVE_VALUES = (True, False, None)`; como `in` usa igualdade, `1`, `0`, `1.0` e `0.0` passam pela validação e são gravados na coluna booleana.
- **Impact:** No SQLite os limites de `String(n)` não são aplicados, então valores fora do contrato entram silenciosamente na base (uma "cor" de 200 caracteres volta intacta em `GET /categories`); com qualquer outro engine apontado por `DATABASE_URL` — PostgreSQL ou MySQL em modo estrito — a mesma requisição vira um erro 500 de persistência em vez de um 400 de validação.
- **Recommendation:** Derivar os limites das constantes do modelo e validá-los no validador (comprimento de `name`/`email`/`description`, formato hexadecimal de `color`), e trocar a checagem de `active` por `isinstance(value, bool)` com `None` tratado à parte. (Playbook T-12)

### [LOW] Duplicated Code — fonte de tempo inconsistente no health check
- **ID:** AP-16
- **File:** `src/controllers/health_controller.py:2`, `src/controllers/health_controller.py:15`
- **Description:** `health()` devolve `'timestamp': str(datetime.now())`, usando o horário local do servidor, enquanto todo o resto da aplicação padroniza UTC por `utcnow_naive()` (`src/utils/datetime_utils.py:5`), inclusive os `created_at`/`updated_at` serializados nas mesmas respostas JSON.
- **Impact:** O timestamp do health check não é comparável com nenhuma outra data da API; em servidor com fuso diferente de UTC a diferença aparente chega a horas ao correlacionar logs e respostas.
- **Recommendation:** Usar `utcnow_naive()` no health controller, eliminando o import direto de `datetime` e a segunda fonte de tempo. (Playbook T-13)

### [LOW] Dead Code — pacote de modelos e parâmetro nunca usados
- **ID:** AP-22
- **File:** `src/models/__init__.py:1-9`, `src/app.py:26`, `src/app.py:35`
- **Description:** `src/models/__init__.py` documenta que "importar o pacote registra todas as entidades no metadata antes do `db.create_all()`", mas nenhum módulo importa `src.models` (grep por `from src.models import` / `import src.models` não retorna ocorrências — todos importam os módulos concretos `src.models.task_model` etc.). O parâmetro `config_overrides` de `create_app()` só aparece na própria assinatura e no `from_mapping`; os dois únicos chamadores (`app.py:8` e `seed.py:7`) nunca o passam.
- **Impact:** Código sem efeito que sugere uma garantia inexistente (o registro no metadata depende hoje apenas da cadeia de imports dos controllers) e uma superfície de API do factory que ninguém exercita nem testa.
- **Recommendation:** Ou passar a importar `src.models` no composition root — tornando a garantia do docstring real — ou remover o `__init__.py` de reexport; remover `config_overrides` enquanto não houver chamador (ex.: suíte de testes) que o utilize. (Playbook T-16)

## Deprecated APIs

None detected

- *Código:* nenhuma ocorrência de `datetime.utcnow()`, `Model.query.get()`, API legada de `Query`, `before_first_request`, `flask.__version__`, `werkzeug.urls` ou `pkg_resources` — a única menção a `utcnow()` é o docstring em `src/utils/datetime_utils.py:8` que explica a substituição.
- *Dependências:* auditoria via API JSON do PyPI (campo `vulnerabilities`) para os 6 pins de `requirements.txt` — flask 3.1.3, flask-sqlalchemy 3.1.1, flask-cors 6.0.5, python-dotenv 1.2.3, werkzeug 3.1.8, itsdangerous 2.2.0 — retornou lista vazia para todos.

```text
================================
Total: 8 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
