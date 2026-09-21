# Audit Report — task-manager-api (auditoria do código já refatorado, após o feedback da avaliação)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.4.0), gerada por `claude -p "/refactor-arch"` dentro de `task-manager-api/`
> (modelo `claude-opus-5[1m]`, sessão `0c4f9654-57b5-4840-9128-37576fbbcc89`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 1 · HIGH 2 · MEDIUM 2 · LOW 2 · Total 7.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.1.3
Files:   39 analyzed | ~1569 lines of code
```

## Summary

CRITICAL: 1 | HIGH: 2 | MEDIUM: 2 | LOW: 2

## Findings

### [CRITICAL] Unprotected Destructive Endpoints and Broken Authentication
- **ID:** AP-06
- **File:** `src/app.py:44-50`, `src/services/auth_service.py:25-26`, `src/views/category_routes.py:9-12`, `src/views/task_routes.py:8-13`, `src/views/user_routes.py:8-14`
- **Description:** Nenhuma das 22 rotas passa por um guard. `create_app()` registra os cinco blueprints e o error handler (`src/app.py:44-50`) sem nenhum `before_request` ou decorator de autenticação, e não existe middleware de auth no projeto (`src/middlewares/` só tem `error_handler.py`). `AuthService.issue_token()` (`src/services/auth_service.py:25-26`) emite um token assinado com `URLSafeTimedSerializer`, mas nenhum módulo chama `loads()`/verificação — o token é decorativo. Assim, `DELETE /users/<id>` (`src/views/user_routes.py:11`), que apaga o usuário **e todas as tasks dele** via `cascade='all, delete'` (`src/models/user_model.py:31`), `DELETE /tasks/<id>` (`src/views/task_routes.py:13`), `DELETE /categories/<id>` (`src/views/category_routes.py:11-12`) e todos os `PUT`/`POST` são executáveis por qualquer cliente anônimo com acesso de rede.
- **Impact:** Destruição total e irreversível dos dados por um cliente não autenticado (um `DELETE /users/1..N` em loop zera usuários e tasks), além de leitura irrestrita de PII — `GET /users` devolve nome, e-mail, role e `active` de todos os usuários. O fluxo de login existe mas não protege nada, dando uma falsa sensação de segurança.
- **Recommendation:** Criar `src/middlewares/auth.py` com um guard que valide o token do header `Authorization` via `AuthService` (`loads()` com `max_age`), carregue o usuário em `flask.g` e recuse com 401/403; aplicar o guard nos blueprints de escrita (`POST`/`PUT`/`DELETE` de tasks, users e categories) e nos relatórios, deixando `/`, `/health` e `POST /login` públicos. Enquanto a autenticação obrigatória não for introduzida (mudança de contrato — ver `mvc-guidelines.md` §9), manter as barreiras que já existem contra escalação de privilégio e documentar a limitação. (Playbook T-06)

### [HIGH] Sensitive Data Exposure in Logs — bound parameters of failed writes
- **ID:** AP-04
- **File:** `src/models/database.py:11`, `src/models/database.py:25-28`, `src/middlewares/error_handler.py:36-37`
- **Description:** A extensão é criada como `db = SQLAlchemy()` (`src/models/database.py:11`) sem `engine_options={'hide_parameters': True}` — não há nenhuma ocorrência de `hide_parameters` no projeto. Em falha de escrita, `commit()` faz `logger.exception('Falha ao gravar no banco')` (`src/models/database.py:27`) e `handle_unexpected_error` faz `logger.exception('Erro não tratado')` (`src/middlewares/error_handler.py:37`); o traceback formata o `SQLAlchemyError`, cujo `__str__` anexa `[SQL: INSERT INTO users ...] [parameters: (...)]` com os valores ligados. Os caminhos `User.register()` → `create()` (`src/models/user_model.py:48-52`) e `user.assign({'password': ...})` → `update()` (`src/models/user_model.py:41-45`) gravam a coluna `password` com o hash `scrypt`, que entra no log.
- **Impact:** Hashes de senha e e-mails dos usuários vão parar em texto claro no log da aplicação sempre que um `INSERT`/`UPDATE` em `users` falhar (ex.: duas requisições `POST /users` concorrentes com o mesmo e-mail passam juntas pela checagem `email_in_use` e uma viola o índice único; em Postgres/MySQL, qualquer violação de `VARCHAR`/`NOT NULL`). Quem tiver acesso aos logs — geralmente mais amplo que o acesso ao banco — obtém material para quebra offline de senhas.
- **Recommendation:** Passar `engine_options={'hide_parameters': True}` ao `SQLAlchemy()`/`init_database()` e trocar `logger.exception` por um log que registre apenas tipo do erro e operação (ex.: `logger.error('Falha ao gravar no banco: %s', type(exc).__name__)`), mantendo o traceback só quando não houver parâmetros sensíveis. (Playbook T-05)

### [HIGH] Sensitive Data Exposure — privileged seed account with a well-known short password
- **ID:** AP-04
- **File:** `src/models/seed.py:14-19`, `src/models/seed.py:60-62`
- **Description:** `SEED_USERS` (`src/models/seed.py:15-19`) cria `joao@email.com` com `'role': 'admin'` e `'password': '1234'`, além de `pedro@email.com` com `'role': 'manager'` e `'password': 'pass'`. O seed aplica as senhas chamando `user.set_password(data['password'])` direto (`src/models/seed.py:62`), sem passar pelos validadores — burlando o `MIN_PASSWORD_LENGTH = 8` que a API exige de qualquer cliente (`src/controllers/validators/user_validator.py:29-30`). O README instrui `python seed.py` como passo obrigatório antes do primeiro boot, então toda instalação nasce com essas contas.
- **Impact:** Credenciais administrativas públicas (estão no repositório) e com 4 caracteres, em um `POST /login` aberto. Hoje o token não concede privilégio algum porque nenhuma rota o verifica, mas no momento em que o guard do AP-06 entrar, essas contas viram acesso admin imediato para qualquer pessoa que leia o código.
- **Recommendation:** Trocar as senhas do seed por valores que respeitem `MIN_PASSWORD_LENGTH` e não sejam adivinháveis (gerar com `secrets.token_urlsafe` e imprimir uma única vez no console, ou ler de variável de ambiente), ou criar os usuários do seed com `active=False`; manter apenas o papel `user` por padrão e documentar que o seed é exclusivo de desenvolvimento. (Playbook T-05)

### [MEDIUM] Missing Input Validation — tags length is never checked
- **ID:** AP-14
- **File:** `src/controllers/validators/task_validator.py:72-79`, `src/controllers/validators/task_validator.py:99`, `src/controllers/validators/task_validator.py:123`, `src/models/task_model.py:24`, `src/models/task_model.py:47`
- **Description:** A coluna é declarada como `tags = db.Column(db.String(MAX_TAGS_LENGTH), ...)` com `MAX_TAGS_LENGTH = 500` (`src/models/task_model.py:24,47`), mas `_tags()` (`src/controllers/validators/task_validator.py:72-79`) só checa o tipo (`list` de `str`, `str` ou `None`) e nunca o comprimento — `MAX_TAGS_LENGTH` não é sequer importado pelo validador (`src/controllers/validators/task_validator.py:4-5`). É o único campo com limite de coluna declarado que escapa da validação: `title`, `name`, `email`, `description` (categoria) e `color` são todos conferidos contra suas constantes.
- **Impact:** Inconsistência de validação entre camadas. Em SQLite o limite de `VARCHAR` não é aplicado e a task é gravada com tags acima do contrato; com `DATABASE_URL` apontando para Postgres/MySQL, um `POST /tasks` ou `PUT /tasks/<id>` com tags longas provoca `DataError` → 500 em entrada inválida comum, e (junto com o AP-04) despeja os parâmetros da query no log.
- **Recommendation:** Importar `MAX_TAGS_LENGTH` em `task_validator.py` e validar o comprimento da representação final (após `Task.encode_tags`, ou seja, da string unida por vírgula) em `_tags()`, levantando `ValidationError(TAGS_INVALID_MESSAGE)` — mesma mensagem já usada para tags inválidas, preservando o contrato. (Playbook T-12)

### [MEDIUM] Duplicated Code — validators and contract messages repeated across modules
- **ID:** AP-16
- **File:** `src/controllers/category_controller.py:15`, `src/controllers/user_controller.py:17`, `src/controllers/validators/category_validator.py:15-20`, `src/controllers/validators/task_validator.py:18`, `src/controllers/validators/task_validator.py:20`, `src/controllers/validators/user_validator.py:34-39`, `src/services/report_service.py:12`
- **Description:** Dois blocos:
  - `_name()` em `category_validator.py:15-20` e `user_validator.py:34-39` são estruturalmente idênticos (checa `isinstance(value, str)`, checa `len(value) > MAX_NAME_LENGTH`, devolve o valor), variando apenas as constantes de mensagem — e os dois `MAX_NAME_LENGTH` valem 100 (`src/models/category_model.py:12`, `src/models/user_model.py:13`).
  - A mesma string de contrato é redeclarada em módulos diferentes: `'Usuário não encontrado'` em `user_controller.py:17`, `task_validator.py:18` e `report_service.py:12`; `'Categoria não encontrada'` em `category_controller.py:15` e `task_validator.py:20`.
- **Impact:** A mensagem de erro é parte do contrato público da API; com três cópias independentes, corrigir o texto em um lugar faz `GET /users/999`, `POST /tasks` com `user_id` inexistente e `GET /reports/user/999` divergirem silenciosamente. O `_name()` duplicado faz o mesmo com as regras de comprimento.
- **Recommendation:** Extrair um helper compartilhado `validate_bounded_text(value, max_length, invalid_message, too_long_message)` em `src/utils/validators.py` e chamá-lo nos dois validadores; mover as mensagens de "não encontrado" para um único ponto por entidade (constante no módulo do model, importada por controller, validador e service). (Playbook T-13)

### [LOW] Dependency Manifest Does Not Declare a Direct Dependency
- **ID:** AP-22
- **File:** `requirements.txt:1-6`, `src/models/category_model.py:4`, `src/models/database.py:5`, `src/models/seed.py:4`, `src/models/task_model.py:5-7`, `src/models/user_model.py:2`
- **Description:** Cinco módulos importam SQLAlchemy diretamente (`from sqlalchemy import and_, case, func, or_, select`, `from sqlalchemy.ext.hybrid import hybrid_method`, `from sqlalchemy.orm import selectinload`, `from sqlalchemy.exc import SQLAlchemyError`, `from sqlalchemy import delete`), mas `requirements.txt` (linhas 1-6) só declara `flask-sqlalchemy==3.1.1`; `sqlalchemy` não aparece. A versão realmente usada (2.0.54, do `.venv`) vem apenas como dependência transitiva.
- **Impact:** A reprodutibilidade do build depende do range de versões que o Flask-SQLAlchemy resolver: uma mudança na faixa transitiva pode trazer uma versão de SQLAlchemy incompatível com as APIs 2.x usadas (`hybrid_method.expression`, `selectinload`, `db.session.get`) sem nenhum sinal no manifesto. O mesmo descuido já foi corrigido para `werkzeug` e `itsdangerous`, que são importados diretamente e estão declarados.
- **Recommendation:** Acrescentar `sqlalchemy==2.0.54` a `requirements.txt`, alinhado com a versão já resolvida, mantendo a convenção de pin exato do arquivo. (Playbook T-16)

### [LOW] Magic Numbers — raw column lengths breaking the file's own convention
- **ID:** AP-20
- **File:** `src/models/task_model.py:40`, `src/models/user_model.py:25-26`
- **Description:** Três colunas usam literais numéricos crus enquanto todas as outras do projeto usam constantes nomeadas: `status = db.Column(db.String(50), ...)` (`src/models/task_model.py:40`), `password = db.Column(db.String(255), ...)` e `role = db.Column(db.String(50), ...)` (`src/models/user_model.py:25-26`). Nos mesmos arquivos, `title`, `tags`, `name` e `email` usam `MAX_TITLE_LENGTH`, `MAX_TAGS_LENGTH`, `MAX_NAME_LENGTH` e `MAX_EMAIL_LENGTH`.
- **Impact:** Baixo — legibilidade e manutenção. O `255` de `password` é especialmente frágil: está acoplado ao tamanho do hash produzido por `generate_password_hash` (`src/models/user_model.py:36`), e trocar o algoritmo para um de saída maior quebraria a gravação em bancos que aplicam o limite, sem nenhuma constante que ligue os dois pontos.
- **Recommendation:** Definir `MAX_STATUS_LENGTH`/`MAX_ROLE_LENGTH` e `MAX_PASSWORD_HASH_LENGTH` no topo dos respectivos módulos de model, junto das demais constantes de comprimento, e referenciá-las nas colunas. (Playbook T-15)

## Deprecated APIs

None detected

- *Código:* nenhuma ocorrência de `datetime.utcnow()`, `Model.query.get()`, `Model.query.filter_by()`, `before_first_request`, `flask.json.JSONEncoder`, `app.env`, `_app_ctx_stack`, `werkzeug.urls`, `distutils` ou `pkg_resources`. `src/utils/datetime_utils.py:5-11` já substitui `datetime.utcnow()` por `datetime.now(timezone.utc).replace(tzinfo=None)`, e todas as consultas usam a API 2.0 (`db.session.get`, `db.session.execute(select(...))`).
- *Dependências:* auditoria via API JSON do PyPI (campo `vulnerabilities`) para os 6 pins de `requirements.txt` — `flask==3.1.3`, `flask-sqlalchemy==3.1.1`, `flask-cors==6.0.5`, `python-dotenv==1.2.3`, `werkzeug==3.1.8`, `itsdangerous==2.2.0` — todos sem vulnerabilidades. As transitivas resolvidas no `.venv` (`sqlalchemy==2.0.54`, `jinja2==3.1.6`, `click==8.5.0`, `blinker==1.9.0`, `markupsafe==3.0.3`, `greenlet==3.5.6`) também vieram limpas.

```text
================================
Total: 7 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
