# Audit Report — task-manager-api

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.1.0), gerada por `claude -p "/refactor-arch"` executado dentro de `task-manager-api/`
> (modelo `claude-opus-5[1m]`, sessão `0934520c-8917-4339-9c6f-a520b79884a6`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 3 · HIGH 6 · MEDIUM 6 · LOW 5 · Total 20.

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0
Files:   15 analyzed | ~1158 lines of code
```

## Summary

CRITICAL: 3 | HIGH: 6 | MEDIUM: 6 | LOW: 5

## Findings

### [CRITICAL] Hardcoded credentials and secrets
- **ID:** AP-01
- **File:** `app.py:13`, `services/notification_service.py:7-10`
- **Description:** A chave de assinatura do Flask está escrita direto no código: `app.config['SECRET_KEY'] = 'super-secret-key-123'`. O `NotificationService.__init__` também fixa as credenciais SMTP: `self.email_user = 'taskmanager@gmail.com'`, `self.email_password = 'senha123'`, host `'smtp.gmail.com'` e porta `587`.
- **Impact:** Quem tem acesso ao repositório pega a senha do e-mail e a chave que assina sessões/tokens, o que permite forjar tokens. Para trocar um segredo é preciso mudar o código e fazer novo deploy, e o mesmo valor vale para todos os ambientes.
- **Recommendation:** Criar `config/settings.py` que leia `SECRET_KEY`, `SMTP_*` e a URI do banco de variáveis de ambiente, sem default secreto (em desenvolvimento, gerar uma chave aleatória temporária). Documentar as variáveis em `.env.example` e trocar a senha que ficou exposta. (Playbook T-01)

### [CRITICAL] Sensitive data exposure (responses and logs)
- **ID:** AP-04
- **File:** `models/user.py:16-25`, `routes/user_routes.py:33`, `routes/user_routes.py:85`, `routes/user_routes.py:129`, `routes/user_routes.py:209`
- **Description:** `User.to_dict()` inclui `'password': self.password` (o hash MD5). Esse dicionário é devolvido sem autenticação por `get_user` (GET /users/<id>), `create_user` (POST /users), `update_user` (PUT /users/<id>) e `login` (POST /login, no campo `user`).
- **Impact:** Qualquer cliente coleta o hash de senha de todos os usuários só percorrendo os IDs. Como são MD5 sem salt de senhas curtas (AP-05), uma rainbow table os reverte na hora e as contas ficam comprometidas.
- **Recommendation:** Serializar usuários com uma lista explícita de campos permitidos, sem `password`, num serializer da camada de views usado por todas as respostas. (Playbook T-05)

### [CRITICAL] Insecure password storage
- **ID:** AP-05
- **File:** `models/user.py:27-32`, `routes/user_routes.py:64`, `routes/user_routes.py:115`, `seed.py:19`, `seed.py:26`, `seed.py:33`
- **Description:** `set_password()` grava `hashlib.md5(pwd.encode()).hexdigest()` sem salt e sem iterações, e `check_password()` compara com `==`, que não é constante no tempo. A regra aceita senhas de 4 caracteres (`len(password) < 4`), e o seed cria contas com `'1234'`, `'abcd'` e `'pass'`.
- **Impact:** Uma GPU calcula bilhões de MD5 por segundo, e senhas iguais geram o mesmo hash. Somado ao vazamento de AP-04, todas as senhas podem ser recuperadas.
- **Recommendation:** Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (scrypt/pbkdf2 com salt). Refazer o hash das senhas do seed e aceitar o MD5 legado no login, atualizando o hash, para não invalidar credenciais existentes. Aumentar o tamanho mínimo de senha muda o contrato e depende de decisão de produto. (Playbook T-04)

### [HIGH] Tight coupling without dependency injection / no composition root
- **ID:** AP-08
- **File:** `app.py:9-20`, `app.py:30-31`, `seed.py:2`, `services/notification_service.py:15`
- **Description:** A aplicação é criada e configurada no momento do import do módulo (`app = Flask(__name__)`, `app.config[...]`, `register_blueprint`), sem um `create_app()`. O `with app.app_context(): db.create_all()` roda como efeito colateral desse import e cria `instance/tasks.db`. O `seed.py` faz `from app import app, db` para reaproveitar esses globais. `NotificationService.send_email` cria `smtplib.SMTP(...)` por conta própria, sem receber a dependência.
- **Impact:** Não dá para criar uma instância com outra configuração (por exemplo, banco em memória para testes), e qualquer import do app já mexe no banco. O cliente SMTP também não pode ser trocado por um fake nos testes.
- **Recommendation:** Criar uma app factory `create_app()` como ponto único de montagem (config → `db.init_app` → blueprints → error handlers), com `db.create_all()` dentro dela. `seed.py` passa a usar `create_app()`, e dependências externas chegam por parâmetro. (Playbook T-11)

### [HIGH] Insecure runtime configuration (debug mode, open bind, wildcard CORS)
- **ID:** AP-10
- **File:** `app.py:15`, `app.py:34`
- **Description:** `app.run(debug=True, host='0.0.0.0', port=5000)` liga o debugger interativo e o reloader do Werkzeug, ouvindo em todas as interfaces. `CORS(app)` sem `origins` responde `Access-Control-Allow-Origin: *` em todas as rotas.
- **Impact:** Erros 500, fáceis de provocar (AP-14), mostram traceback e trechos do código para qualquer máquina da rede. O console do debugger executa código se alguém obtiver o PIN. Qualquer site consegue chamar a API pelo navegador da vítima.
- **Recommendation:** Ler `FLASK_DEBUG` (default `False`), `HOST`, `PORT` (default `5000`) e `CORS_ORIGINS` de variáveis de ambiente, com defaults seguros. (Playbook T-01)

### [HIGH] Deprecated / obsolete APIs and dependencies — vulnerable pinned packages
- **ID:** AP-18
- **File:** `requirements.txt:1`, `requirements.txt:3`, `requirements.txt:4`, `requirements.txt:5`, `requirements.txt:6`
- **Description:** A consulta à API JSON do PyPI (campo `vulnerabilities`, fonte OSV) mostrou alertas de segurança para as versões fixadas:
  - `flask-cors==4.0.0`, usado por `CORS(app)`: CVE-2024-1681 (injeção em log, corrigida na 4.0.1), CVE-2024-6221 (`Access-Control-Allow-Private-Network` ligado por padrão, corrigida na 4.0.2) e CVE-2024-6844, CVE-2024-6866 e CVE-2024-6839 (comparação de caminhos inconsistente, corrigidas na 6.0.0).
  - `flask==3.0.0`: CVE-2026-27205 (falta o header `Vary: Cookie` quando `session` é acessada, corrigida na 3.1.3).
  - Dependências que nem são importadas: `marshmallow==3.20.1` (CVE-2025-68480), `requests==2.31.0` (CVE-2024-35195, CVE-2024-47081, CVE-2026-25645) e `python-dotenv==1.0.0` (CVE-2026-28684).
- **Impact:** Junto com o CORS aberto e o bind em `0.0.0.0` (AP-10), páginas públicas podem alcançar a API dentro de redes privadas. Os pacotes vulneráveis sem uso aumentam a superfície de ataque sem trazer nada.
- **Recommendation:** Atualizar `flask-cors` para ≥ 6.0.0 e `flask` para ≥ 3.1.3, confirmando o boot depois. Remover `marshmallow`, `requests` e `python-dotenv` se continuarem sem uso; se o `python-dotenv` for adotado para a config, usar ≥ 1.2.2. (Playbook T-14)

### [HIGH] God Class / God module — reports and categories in the same blueprint
- **ID:** AP-03
- **File:** `routes/report_routes.py:10-223`
- **Description:** O `report_routes.py` registra no mesmo blueprint `report_bp` (`'reports'`) dois domínios sem relação: os relatórios (`summary_report`, `user_report`) e o CRUD completo de categorias (`get_categories`, `create_category`, `update_category`, `delete_category`, linhas 157-223). Cada handler mistura leitura de `request`, consultas `Task.query`/`Category.query`/`db.session` e agregações. As entidades já estão separadas em `models/`, por isso a severidade é HIGH e não CRITICAL.
- **Impact:** As rotas de categoria ficam escondidas num módulo de relatórios. Mudanças nos dois domínios se chocam no mesmo arquivo, e nenhuma lógica pode ser reutilizada ou testada sem HTTP.
- **Recommendation:** Separar por domínio: `controllers/category_controller.py` + `views/category_routes.py` para categorias, e `controllers/report_controller.py` + `services/report_service.py` para as agregações que envolvem várias entidades. (Playbook T-03)

### [HIGH] Business logic in routes/controllers (fat controller)
- **ID:** AP-07
- **File:** `routes/report_routes.py:13-101`, `routes/report_routes.py:104-155`, `routes/task_routes.py:12-63`, `routes/task_routes.py:86-154`, `routes/task_routes.py:157-223`, `routes/task_routes.py:274-299`, `routes/user_routes.py:43-90`, `routes/user_routes.py:93-132`, `routes/user_routes.py:135-151`
- **Description:** Não existe camada de controllers, e os handlers fazem tudo:
  - Validam campo a campo (`create_task` tem 69 linhas, `update_task` tem 67).
  - Acessam `Task.query`, `User.query` e `db.session` diretamente.
  - Aplicam regras de negócio: cálculo de atraso, `completion_rate`, contagens por status e prioridade (`summary_report` tem 89 linhas; `task_stats`).
  - Decidem a exclusão em cascata das tarefas em `delete_user` (`for t in tasks: db.session.delete(t)`).

  Os métodos de domínio que já existem no model (`Task.validate_status`, `Task.validate_priority`, `Task.is_overdue`, `User.is_admin`) são ignorados, e as rotas não usam nada de `services/` nem de `utils/`.
- **Impact:** As regras não podem ser testadas nem reaproveitadas sem subir o Flask. Cada rota nova copia a lógica (AP-16), e mudar uma regra obriga a editar vários handlers.
- **Recommendation:** As rotas só ligam URL a controller. O controller lê a entrada, valida e escolhe o status HTTP. Consultas e regras de cada entidade vão para os models; agregações com várias entidades vão para `services/`. (Playbook T-03, T-13)

### [HIGH] Unprotected destructive/debug endpoints and broken authentication
- **ID:** AP-06
- **File:** `routes/user_routes.py:52`, `routes/user_routes.py:71-72`, `routes/user_routes.py:119-122`, `routes/user_routes.py:207-211`
- **Description:** O `login` devolve `'token': 'fake-jwt-token-' + str(user.id)`, um token previsível, sem assinatura e que nenhuma rota verifica. O `create_user` aceita `role = data.get('role', 'user')` vindo do corpo, então qualquer um se cadastra como `admin`. O `update_user` deixa trocar `role` e `password` de qualquer usuário. Nenhuma rota exige autenticação, nem as de exclusão (`DELETE /users/<id>`, `DELETE /tasks/<id>`, `DELETE /categories/<id>`).
- **Impact:** Qualquer cliente pode se registrar como administrador, forjar o token de qualquer usuário sabendo só o ID, redefinir a senha de outra conta ou apagar usuários junto com todas as tarefas deles.
- **Recommendation:** Emitir um token assinado (`itsdangerous.URLSafeTimedSerializer(SECRET_KEY)`), mantendo o campo `token` na resposta. Exigir autenticação nas rotas de escrita e restringir a atribuição de `role` muda o contrato público e depende de decisão de produto. (Playbook T-06)

### [MEDIUM] Deprecated / obsolete APIs and dependencies — `datetime.utcnow()`
- **ID:** AP-18
- **File:** `models/category.py:11`, `models/task.py:15-16`, `models/task.py:52`, `models/user.py:14`, `routes/report_routes.py:35`, `routes/report_routes.py:42`, `routes/report_routes.py:45`, `routes/report_routes.py:71`, `routes/report_routes.py:133`, `routes/task_routes.py:31`, `routes/task_routes.py:72`, `routes/task_routes.py:215`, `routes/task_routes.py:285`, `routes/user_routes.py:172`, `seed.py:66-67`, `seed.py:69-70`, `seed.py:74`, `services/notification_service.py:35`, `utils/helpers.py:38`
- **Description:** `datetime.utcnow()` está deprecated desde o Python 3.12. Ele aparece em chamadas diretas e como `default=datetime.utcnow`/`onupdate=datetime.utcnow` nas colunas `created_at`/`updated_at`. O projeto não fixa versão de runtime, e o interpretador local (3.14.7) emite `DeprecationWarning` a cada chamada.
- **Impact:** Gera warnings a cada request e vai quebrar quando a função for removida. Além disso, datetimes UTC sem fuso se confundem fácil com hora local (o `/health` usa `datetime.now()`).
- **Recommendation:** Criar um helper único `utc_now()` baseado em `datetime.now(timezone.utc)`, removendo o `tzinfo` antes de gravar ou serializar para manter o formato atual das datas, e usá-lo em models, services e seed. (Playbook T-14)

### [MEDIUM] Duplicated code
- **ID:** AP-16
- **File:** `models/task.py:38-60`, `routes/report_routes.py:34-36`, `routes/report_routes.py:132-135`, `routes/task_routes.py:17-28`, `routes/task_routes.py:30-39`, `routes/task_routes.py:71-80`, `routes/task_routes.py:96-100`, `routes/task_routes.py:110-114`, `routes/task_routes.py:167-170`, `routes/task_routes.py:177-183`, `routes/task_routes.py:283-287`, `routes/user_routes.py:61`, `routes/user_routes.py:71`, `routes/user_routes.py:106`, `routes/user_routes.py:120`, `routes/user_routes.py:171-180`, `utils/helpers.py:21`, `utils/helpers.py:75`, `utils/helpers.py:110-111`
- **Description:**
  - A regra de atraso (`if t.due_date < datetime.utcnow():` + `if t.status != 'done' and t.status != 'cancelled':`) foi copiada em 6 lugares, embora `Task.is_overdue()` (`models/task.py:50-60`) faça exatamente isso e nunca seja chamado.
  - `get_tasks` remonta à mão os campos que `Task.to_dict()` já produz (`routes/task_routes.py:17-28`).
  - As validações de título (3–200), status e prioridade (1–5) se repetem em `create_task` e `update_task`, apesar de existirem `Task.validate_status`, `Task.validate_priority` e `utils.helpers.process_task_data`.
  - A lista `['pending', 'in_progress', 'done', 'cancelled']`, a lista `['user', 'admin', 'manager']` e o regex de e-mail `^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$` estão repetidos entre rotas, model e `utils/helpers.py`.
- **Impact:** Uma correção de regra precisa ser feita em vários lugares, e as cópias já divergem: `process_task_data` faz `strip()` e aceita data `DD/MM/YYYY`, as rotas não.
- **Recommendation:** Ter uma única fonte por regra: constantes de domínio e `Task.is_overdue()` no model, validadores compartilhados entre create e update, e uma serialização única nas views. (Playbook T-13)

### [MEDIUM] N+1 queries and per-row aggregation
- **ID:** AP-13
- **File:** `routes/report_routes.py:15-28`, `routes/report_routes.py:30-43`, `routes/report_routes.py:53-68`, `routes/report_routes.py:159-164`, `routes/task_routes.py:41-57`, `routes/task_routes.py:275-287`, `routes/user_routes.py:14-22`
- **Description:**
  - `get_tasks` roda `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` para cada tarefa (1 + 2N queries).
  - `get_users` acessa `len(u.tasks)`, que carrega as tarefas de cada usuário. `get_categories` roda `Task.query.filter_by(category_id=c.id).count()` por categoria. `summary_report` roda `Task.query.filter_by(user_id=u.id).all()` por usuário.
  - `summary_report` faz 12 `COUNT` separados (totais, status e prioridades 1–5) e `task_stats` faz mais 5. Ambos ainda carregam `Task.query.all()` para contar as atrasadas em Python.
- **Impact:** O número de queries cresce junto com tarefas, usuários e categorias, e os relatórios trazem a tabela inteira para a memória. Com volume real, a latência piora rápido.
- **Recommendation:** Usar `GROUP BY` (`db.func.count` agrupado por status, prioridade, usuário e categoria), filtrar as atrasadas no SQL (`due_date < now AND status NOT IN (...)`) e usar eager loading (`joinedload`/`selectinload`) para trazer nomes de usuário e categoria. (Playbook T-08)

### [MEDIUM] Deprecated / obsolete APIs and dependencies — legacy `Query.get()`
- **ID:** AP-18
- **File:** `routes/report_routes.py:105`, `routes/report_routes.py:192`, `routes/report_routes.py:213`, `routes/task_routes.py:42`, `routes/task_routes.py:51`, `routes/task_routes.py:67`, `routes/task_routes.py:117`, `routes/task_routes.py:122`, `routes/task_routes.py:158`, `routes/task_routes.py:188`, `routes/task_routes.py:195`, `routes/task_routes.py:227`, `routes/user_routes.py:29`, `routes/user_routes.py:94`, `routes/user_routes.py:136`, `routes/user_routes.py:155`
- **Description:** `Model.query.get(id)` (por exemplo `Task.query.get(task_id)`, `User.query.get(user_id)`) é API legada no SQLAlchemy 2.x, que o `flask-sqlalchemy==3.1.1` exige, e emite `LegacyAPIWarning`.
- **Impact:** Toda busca por ID gera warning, e a remoção prevista numa versão futura obrigaria a mexer em 16 pontos espalhados pelas rotas.
- **Recommendation:** Trocar por `db.session.get(Model, id)` dentro de métodos de acesso nos models. (Playbook T-14)

### [MEDIUM] Missing or inconsistent input validation
- **ID:** AP-14
- **File:** `routes/report_routes.py:177-180`, `routes/report_routes.py:196-202`, `routes/task_routes.py:96-100`, `routes/task_routes.py:113`, `routes/task_routes.py:140-144`, `routes/task_routes.py:167-170`, `routes/task_routes.py:182`, `routes/task_routes.py:260-264`, `routes/user_routes.py:61-65`, `routes/user_routes.py:102-103`, `routes/user_routes.py:124-125`
- **Description:**
  - Tipos não verificados viram erro 500:
    - `priority < 1` com `"priority": "alta"` (`TypeError`).
    - `len(title)` com `"title": 123`, ou com `null` no update.
    - `re.match`/`len(password)` com e-mail ou senha numéricos.
    - `','.join(tags)` com `[1, 2]`.
    - `int(priority)`/`int(user_id)` em `GET /tasks/search?priority=abc` (`ValueError`).
    - `'name' in data` quando o corpo JSON é `null` em `update_category`.
    - `active` não booleano em `update_user`, que falha no commit.
  - As regras de create e update não batem: o `name` de categoria e de usuário é obrigatório no POST, mas aceita vazio no PUT. `color` nunca é validada (`is_valid_color` existe, mas ninguém chama), e `tags` aceita qualquer tipo.
- **Impact:** Entradas inválidas comuns derrubam a requisição com 500, que com `debug=True` ainda expõe o traceback, e deixam gravar dados incoerentes.
- **Recommendation:** Criar uma camada de validação por entidade, compartilhada por create e update, que confira tipo e faixa de valores e responda 400 com `{'error': ...}`. (Playbook T-12)

### [MEDIUM] Swallowed / generic exception handling, no centralized error handler
- **ID:** AP-15
- **File:** `routes/report_routes.py:186-188`, `routes/report_routes.py:207-209`, `routes/report_routes.py:221-223`, `routes/task_routes.py:62-63`, `routes/task_routes.py:137-138`, `routes/task_routes.py:151-154`, `routes/task_routes.py:204-205`, `routes/task_routes.py:221-223`, `routes/task_routes.py:236-238`, `routes/user_routes.py:87-90`, `routes/user_routes.py:130-132`, `routes/user_routes.py:149-151`, `utils/helpers.py:46-50`, `utils/helpers.py:88-89`
- **Description:** Há 12 `except:` sem tipo (9 nas rotas, 3 em `utils/helpers.py`) e 3 `except Exception as e`: dois só fazem `print(str(e))` e o terceiro descarta o erro. O `get_tasks`, por exemplo, envolve o handler inteiro em `try` e responde `jsonify({'error': 'Erro interno'}), 500`. Cada handler repete seu próprio try/rollback, e o `app.py` não registra nenhum `@app.errorhandler`. Por isso, exceções não tratadas (AP-14), rotas inexistentes (404) e métodos não permitidos (405) respondem com HTML do Flask/Werkzeug em vez do formato JSON `{'error': ...}`.
- **Impact:** Bugs reais ficam escondidos sem log útil (o `except:` sem tipo captura até `KeyboardInterrupt`/`SystemExit`), e o cliente recebe erros em formatos diferentes.
- **Recommendation:** Criar exceções da aplicação (`ValidationError`, `NotFoundError`, `ConflictError`) e handlers centralizados em `middlewares/error_handler.py`, que registrem o stack trace com `logging` e sempre respondam `{'error': ...}`. Remover os try/except repetidos. (Playbook T-07)

### [LOW] Dead code and unused imports/dependencies
- **ID:** AP-22
- **File:** `app.py:7`, `models/task.py:3`, `models/task.py:38-60`, `models/user.py:34-38`, `requirements.txt:4-6`, `routes/report_routes.py:7-8`, `routes/task_routes.py:7`, `routes/user_routes.py:6`, `services/notification_service.py:1-48`, `utils/helpers.py:3-7`, `utils/helpers.py:9-116`
- **Description:**
  - Imports sem uso:
    - `os, sys, json` em `app.py`.
    - `json, os, sys, time` em `routes/task_routes.py`.
    - `hashlib, json` em `routes/user_routes.py`.
    - `format_date, calculate_percentage` e `json` em `routes/report_routes.py`.
    - `json` em `models/task.py`.
    - `os, json, sys, math, hashlib` em `utils/helpers.py`.
  - Código nunca chamado:
    - `Task.validate_status`, `Task.validate_priority`, `Task.is_overdue` e `User.is_admin`.
    - Tudo de `utils/helpers.py`: `format_date`, `calculate_percentage`, `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data` e as 7 constantes das linhas 110-116.
    - `NotificationService`, que nunca é importado e ainda guarda notificações numa lista em memória (`self.notifications`) perdida a cada restart.
  - Dependências declaradas e nunca importadas: `marshmallow`, `requests` e `python-dotenv`.
- **Impact:** O código morto passa a impressão de que validações e notificações estão ativas, e aumenta o que precisa ser mantido e a superfície de vulnerabilidades (AP-18).
- **Recommendation:** Remover imports e dependências sem uso. Aproveitar no model e nos validadores o que servir (`is_overdue`, constantes) e apagar o resto. Decidir entre ligar o `NotificationService` pela app factory ou removê-lo. (Playbook T-16)

### [LOW] Magic numbers and strings
- **ID:** AP-20
- **File:** `app.py:11`, `app.py:34`, `routes/report_routes.py:24-28`, `routes/report_routes.py:45`, `routes/report_routes.py:129`, `routes/report_routes.py:180`, `routes/task_routes.py:96`, `routes/task_routes.py:99`, `routes/task_routes.py:113`, `routes/task_routes.py:167`, `routes/task_routes.py:169`, `routes/task_routes.py:182`, `routes/user_routes.py:64`, `routes/user_routes.py:115`
- **Description:** Há vários valores literais soltos no código:
  - tamanho de título `3`/`200`;
  - prioridade `1`–`5`, com `priority=1` a `priority=5` mapeadas para `'critical'`, `'high'`, `'medium'`, `'low'` e `'minimal'`;
  - "alta prioridade" definida como `t.priority <= 2`;
  - janela de `timedelta(days=7)`;
  - senha mínima de `4`;
  - cor `'#000000'`;
  - URI `'sqlite:///tasks.db'` e porta `5000` fixas.

  Os status `'pending'`, `'in_progress'`, `'done'` e `'cancelled'` aparecem repetidos como strings. As constantes equivalentes existem em `utils/helpers.py:110-116`, mas ninguém as usa.
- **Impact:** Mudar um limite exige caçar literais em vários arquivos, e o significado de cada número fica implícito.
- **Recommendation:** Criar constantes nomeadas no model (`VALID_STATUSES`, `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `HIGH_PRIORITY_THRESHOLD`, `RECENT_ACTIVITY_DAYS`) e mover URI e porta para `config/`. (Playbook T-15)

### [LOW] Poor naming
- **ID:** AP-21
- **File:** `models/category.py:14`, `models/task.py:45`, `models/user.py:27`, `models/user.py:31`, `routes/report_routes.py:10`, `routes/report_routes.py:24-28`, `routes/report_routes.py:161`, `routes/task_routes.py:16`, `routes/user_routes.py:14`
- **Description:** Há nomes pouco claros: `p1` a `p5` para contagens por prioridade, `d` em `Category.to_dict`, `p` em `validate_priority` e `pwd` em `set_password`/`check_password`. Também há `t`, `u` e `c` em laços longos (o de `get_tasks` tem 44 linhas). O blueprint `report_bp` (`'reports'`) contém as rotas de categorias.
- **Impact:** O código fica mais lento de ler, e o nome do módulo/blueprint engana sobre o que ele contém.
- **Recommendation:** Usar nomes descritivos (`count_by_priority`, `task`, `user`, `category`, `password`) e nomear os módulos pelo domínio. (Playbook T-15)

### [LOW] Verbose / non-idiomatic conditionals
- **ID:** AP-24
- **File:** `models/task.py:39-43`, `models/task.py:46-48`, `models/task.py:51-60`, `models/user.py:35-38`, `routes/task_routes.py:141`, `routes/task_routes.py:210`, `utils/helpers.py:21-23`, `utils/helpers.py:53-55`, `utils/helpers.py:103`
- **Description:** Há condicionais mais longas que o necessário: `if new_status in valid: return True else: return False`, `if self.role == 'admin': return True else: return False`, três `if` aninhados em `is_overdue()` para uma única expressão booleana, e `type(tags) == list` no lugar de `isinstance`.
- **Impact:** O código fica mais longo e difícil de ler, e `type(...) ==` não aceita subclasses.
- **Recommendation:** Escrever `return new_status in VALID_STATUSES`, `return self.role == 'admin'`, `return self.due_date is not None and self.due_date < now and self.status not in ('done', 'cancelled')` e `isinstance(tags, list)`. (Playbook T-16)

### [LOW] print/console logging instead of a logger
- **ID:** AP-23
- **File:** `routes/task_routes.py:149`, `routes/task_routes.py:153`, `routes/task_routes.py:219`, `routes/task_routes.py:234`, `routes/user_routes.py:83`, `routes/user_routes.py:89`, `routes/user_routes.py:147`, `services/notification_service.py:21`, `services/notification_service.py:24`, `utils/helpers.py:39-41`
- **Description:** Eventos e erros são registrados com `print(...)`, sem níveis nem configuração (por exemplo `print(f"Task criada: {task.id} - {task.title}")` e `print(f"ERRO: {str(e)}")`). O `NotificationService` imprime o e-mail do destinatário em `print(f"Email enviado para {to}")`. Os `print` de `seed.py` são saída de linha de comando e ficaram de fora.
- **Impact:** Sem nível, horário e stack trace, não dá para filtrar os logs nem mandá-los para um coletor, e dados pessoais acabam no stdout.
- **Recommendation:** Usar `logging.getLogger(__name__)` configurado na app factory, com `logger.exception` no error handler e sem dados pessoais nas mensagens. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `models/category.py:11`, `models/task.py:15-16`, `models/task.py:52`, `models/user.py:14`, `routes/report_routes.py:35`, `routes/report_routes.py:42`, `routes/report_routes.py:45`, `routes/report_routes.py:71`, `routes/report_routes.py:133`, `routes/task_routes.py:31`, `routes/task_routes.py:72`, `routes/task_routes.py:215`, `routes/task_routes.py:285`, `routes/user_routes.py:172`, `seed.py:66-67`, `seed.py:69-70`, `seed.py:74`, `services/notification_service.py:35`, `utils/helpers.py:38` | `datetime.utcnow()`: deprecated desde o Python 3.12 (interpretador local 3.14.7) | `datetime.now(timezone.utc)` |
| `routes/report_routes.py:105`, `routes/report_routes.py:192`, `routes/report_routes.py:213`, `routes/task_routes.py:42`, `routes/task_routes.py:51`, `routes/task_routes.py:67`, `routes/task_routes.py:117`, `routes/task_routes.py:122`, `routes/task_routes.py:158`, `routes/task_routes.py:188`, `routes/task_routes.py:195`, `routes/task_routes.py:227`, `routes/user_routes.py:29`, `routes/user_routes.py:94`, `routes/user_routes.py:136`, `routes/user_routes.py:155` | `Model.query.get(id)`: Query API legada no SQLAlchemy 2.x (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `requirements.txt:1` | `flask==3.0.0`: CVE-2026-27205 | `flask>=3.1.3` |
| `requirements.txt:3` | `flask-cors==4.0.0`: CVE-2024-1681, CVE-2024-6221, CVE-2024-6844, CVE-2024-6866, CVE-2024-6839 | `flask-cors>=6.0.0` |
| `requirements.txt:4` | `marshmallow==3.20.1` (não importado): CVE-2025-68480 | remover (ou `marshmallow>=3.26.2`) |
| `requirements.txt:5` | `requests==2.31.0` (não importado): CVE-2024-35195, CVE-2024-47081, CVE-2026-25645 | remover (ou `requests>=2.33.0`) |
| `requirements.txt:6` | `python-dotenv==1.0.0` (não importado): CVE-2026-28684 | remover (ou `python-dotenv>=1.2.2`) |

```text
================================
Total: 20 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
