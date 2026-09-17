# Audit Report — task-manager-api

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.2.0), gerada por `claude -p "/refactor-arch"` executado dentro de `task-manager-api/`
> (modelo `claude-opus-5[1m]`, sessão `a2f7fa21-81bb-4e40-90fd-9529573e7307`). Nenhuma edição manual foi feita no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 3 · HIGH 6 · MEDIUM 7 · LOW 5 · Total 21.

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

CRITICAL: 3 | HIGH: 6 | MEDIUM: 7 | LOW: 5

## Findings

### [CRITICAL] Hardcoded Credentials and Secrets
- **ID:** AP-01
- **File:** `app.py:13`, `services/notification_service.py:7-10`
- **Description:** A chave de assinatura do Flask está fixa no código (`app.config['SECRET_KEY'] = 'super-secret-key-123'`), assim como as credenciais SMTP em `NotificationService.__init__` (`self.email_user = 'taskmanager@gmail.com'`, `self.email_password = 'senha123'`, host `smtp.gmail.com`, porta `587`).
- **Impact:** Quem tiver acesso ao repositório fica com a senha do e-mail e com a chave que assina sessões e cookies, e pode forjá-los. O segredo fica para sempre no histórico do git, e trocá-lo exige um novo deploy.
- **Recommendation:** Ler `SECRET_KEY` e as credenciais SMTP de variáveis de ambiente em `config/`, sem default secreto, e criar um `.env.example` só com placeholders. Trocar os valores já expostos. (Playbook T-01)

### [CRITICAL] Sensitive Data Exposure
- **ID:** AP-04
- **File:** `models/user.py:21`, `routes/user_routes.py:33`, `routes/user_routes.py:85`, `routes/user_routes.py:89`, `routes/user_routes.py:129`, `routes/user_routes.py:209`
- **Description:** `User.to_dict()` inclui `'password': self.password` (o hash MD5). Esse método monta as respostas de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login`. Além disso, `create_user()` executa `print(f"ERRO: {str(e)}")`, e o texto da exceção do SQLAlchemy traz os parâmetros do INSERT, hash incluído.
- **Impact:** Sem autenticação, qualquer cliente lê o hash de senha de qualquer usuário. Como é MD5 sem salt (AP-05), senhas como `1234` (seed) são revertidas na hora com rainbow tables.
- **Recommendation:** Criar um serializer de usuário que nunca devolve `password` (campo só de escrita) e trocar o `print` da exceção por um logger que não registra parâmetros SQL. (Playbook T-05)

### [CRITICAL] Insecure Password Storage
- **ID:** AP-05
- **File:** `models/user.py:27-32`, `routes/user_routes.py:64`, `routes/user_routes.py:115`
- **Description:** `set_password()` grava `hashlib.md5(pwd.encode()).hexdigest()`, e `check_password()` compara com o mesmo MD5, sem salt e sem fator de custo. O mínimo exigido é de apenas 4 caracteres (`len(password) < 4`).
- **Impact:** O hash é rápido e sem salt: os hashes vazados (AP-04) caem em segundos por força bruta, e senhas iguais geram hashes iguais.
- **Recommendation:** Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (hash com salt e custo) e, para não quebrar logins existentes, aceitar o MD5 legado e regravar com o novo hash no próximo login. Aumentar o mínimo para 8 caracteres muda o contrato e depende de decisão de produto. (Playbook T-04)

### [HIGH] Tight Coupling / No Composition Root
- **ID:** AP-08
- **File:** `app.py:9-31`, `seed.py:2`, `services/notification_service.py:15`
- **Description:** `app = Flask(__name__)` é criado e configurado no import do módulo, sem `create_app()`, e `db.create_all()` roda como efeito colateral desse import (`with app.app_context():`). `seed.py` faz `from app import app, db` para reaproveitar a instância global, e `send_email()` cria `smtplib.SMTP(...)` diretamente.
- **Impact:** Não dá para subir a app com outra configuração (por exemplo, um banco de teste) sem editar o código. Qualquer import de `app` cria o arquivo de banco, e as dependências concretas não podem ser trocadas em testes.
- **Recommendation:** Criar uma factory `create_app(config)` como composition root, criar o schema dentro dela, fazer o seed usar a factory e injetar o cliente SMTP no serviço. (Playbook T-11)

### [HIGH] Insecure Runtime Configuration
- **ID:** AP-10
- **File:** `app.py:15`, `app.py:34`
- **Description:** `app.run(debug=True, host='0.0.0.0', port=5000)` liga o debugger interativo do Werkzeug e escuta em todas as interfaces. Além disso, `CORS(app)` sem `origins` libera qualquer origem em todas as rotas (sozinho, isso seria MEDIUM).
- **Impact:** O debugger executa código Python arbitrário, protegido só por um PIN, e fica exposto na rede. Exceções mostram stack trace e código-fonte, e o CORS aberto permite que qualquer site chame a API a partir do navegador da vítima.
- **Recommendation:** Ler `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` de variáveis de ambiente, com defaults seguros (debug desligado). A porta 5000 e o comando `python app.py` continuam iguais. (Playbook T-01)

### [HIGH] Deprecated / Vulnerable Dependencies — runtime packages
- **ID:** AP-18
- **File:** `requirements.txt:1`, `requirements.txt:3`
- **Description:** A consulta à API JSON do PyPI mostrou vulnerabilidades em dois pacotes carregados em runtime (`app.py:1-2`):
  - `flask==3.0.0`: CVE-2026-27205 (não envia `Vary: Cookie` ao acessar `session`; corrigido em 3.1.3).
  - `flask-cors==4.0.0`: CVE-2024-1681 (log injection; corrigido em 4.0.1), CVE-2024-6221 (`Access-Control-Allow-Private-Network`; corrigido em 4.0.2) e CVE-2024-6844, CVE-2024-6866, CVE-2024-6839 (comparação de path inconsistente; corrigidos em 6.0.0).
  - As dependências transitivas Werkzeug e SQLAlchemy não têm versão fixada.
- **Impact:** Respostas com dados de sessão podem ser guardadas por caches compartilhados, e a política de CORS pode ser aplicada de forma diferente da configurada. Sem versão fixada nas transitivas, as instalações não são reproduzíveis.
- **Recommendation:** Atualizar para `flask>=3.1.3` e `flask-cors>=6.0.0`, confirmando com boot e smoke test. (Playbook T-14)

### [HIGH] God Class / God Module
- **ID:** AP-03
- **File:** `routes/report_routes.py:1-223`
- **Description:** O blueprint `report_bp` junta dois domínios sem relação: os relatórios (`summary_report`, `user_report`) e o CRUD completo de categorias (`get_categories`, `create_category`, `update_category`, `delete_category`). Nos dois domínios, o mesmo arquivo mistura rotas, consultas ORM (`Task.query...count()`, `db.session.commit()`) e regras de negócio (agregações, taxa de conclusão, atraso).
- **Impact:** O recurso `/categories` fica escondido num módulo de "reports". Qualquer mudança em um domínio mexe no arquivo do outro, e nada pode ser testado sem HTTP e banco.
- **Recommendation:** Separar em `views` + `controllers` de categorias e de relatórios, com as agregações movidas para métodos de model. (Playbook T-03)

### [HIGH] Business Logic in Routes (Fat Controller)
- **ID:** AP-07
- **File:** `routes/report_routes.py:12-101`, `routes/report_routes.py:103-155`, `routes/task_routes.py:11-63`, `routes/task_routes.py:85-154`, `routes/task_routes.py:156-223`, `routes/task_routes.py:273-299`, `routes/user_routes.py:42-90`, `routes/user_routes.py:92-132`, `routes/user_routes.py:134-151`, `routes/user_routes.py:153-183`
- **Description:** Não existe camada de controller, e as funções de rota fazem todo o trabalho:
  - `summary_report()` tem 90 linhas e calcula contagens por status e prioridade, atrasos, atividade dos últimos 7 dias e produtividade por usuário.
  - `create_task()` e `update_task()` têm cerca de 70 linhas cada, com validação, checagem de chaves estrangeiras e conversão de tags.
  - `delete_user()` decide sozinha apagar em cascata as tasks do usuário.
  - Todas acessam `Model.query` e `db.session` diretamente.
  
  As regras que já existem no model (`Task.validate_status`, `Task.validate_priority`, `Task.is_overdue`) não são usadas, e nenhuma rota importa algo de `services/`.
- **Impact:** A regra de negócio fica presa ao HTTP, repetida entre rotas e impossível de testar isoladamente. Qualquer mudança de regra obriga a editar vários handlers.
- **Recommendation:** Criar controllers finos por domínio (lê a entrada, valida, chama o model ou serviço e escolhe o status). A regra de atraso e a validação vão para o model `Task`, e consultas e agregações viram métodos de model. (Playbook T-03, T-13)

### [HIGH] Broken Authentication / Privilege Escalation
- **ID:** AP-06
- **File:** `routes/user_routes.py:52`, `routes/user_routes.py:71-72`, `routes/user_routes.py:119-122`, `routes/user_routes.py:207-211`
- **Description:** O token de login é falso e o controle de acesso não existe:
  - `POST /login` devolve `'token': 'fake-jwt-token-' + str(user.id)`: um token previsível, não assinado e que nenhuma rota verifica.
  - `create_user()` aceita `role = data.get('role', 'user')` do corpo da requisição, então qualquer pessoa se cadastra como `admin`.
  - `update_user()` troca `role` e `active` de qualquer usuário.
  - Nenhuma rota exige autenticação, nem `DELETE /users/<id>`, que também apaga as tasks do usuário.
- **Impact:** A escalada de privilégio é trivial. Qualquer pessoa monta o "token" de outro usuário trocando o id, e dados podem ser alterados ou apagados anonimamente.
- **Recommendation:** Emitir um token assinado e com expiração (por exemplo, `itsdangerous` com a `SECRET_KEY` vinda da config), mantendo o campo `token` na resposta. Não aceitar `role` privilegiado no auto-cadastro. Exigir autenticação em todas as rotas quebra o contrato atual e precisa de decisão de produto. (Playbook T-06)

### [MEDIUM] Deprecated API — `datetime.utcnow()`
- **ID:** AP-18
- **File:** `models/category.py:11`, `models/task.py:15-16`, `models/task.py:52`, `models/user.py:14`, `routes/report_routes.py:35`, `routes/report_routes.py:42`, `routes/report_routes.py:45`, `routes/report_routes.py:71`, `routes/report_routes.py:133`, `routes/task_routes.py:31`, `routes/task_routes.py:72`, `routes/task_routes.py:215`, `routes/task_routes.py:285`, `routes/user_routes.py:172`, `seed.py:66`, `seed.py:67`, `seed.py:69`, `seed.py:70`, `seed.py:74`, `services/notification_service.py:35`, `utils/helpers.py:38`
- **Description:** `datetime.utcnow()` aparece tanto em chamadas diretas quanto como `default=`/`onupdate=` das colunas `created_at`/`updated_at`. A função está deprecated desde o Python 3.12 e gera `DeprecationWarning` no interpretador local (3.14.7).
- **Impact:** Gera warnings em runtime e vai quebrar quando a função for removida. O datetime retornado não tem fuso (naive), o que favorece erros de fuso.
- **Recommendation:** Criar um único helper `utc_now()` baseado em `datetime.now(timezone.utc)`, removendo o `tzinfo` para manter o formato atual das datas nas respostas e as comparações com as colunas do SQLite. (Playbook T-14)

### [MEDIUM] Duplicated Code
- **ID:** AP-16
- **File:** `models/task.py:39`, `routes/report_routes.py:19-22`, `routes/report_routes.py:33-36`, `routes/report_routes.py:132-135`, `routes/task_routes.py:17-28`, `routes/task_routes.py:30-39`, `routes/task_routes.py:71-80`, `routes/task_routes.py:110`, `routes/task_routes.py:140-144`, `routes/task_routes.py:177`, `routes/task_routes.py:209-213`, `routes/task_routes.py:276-287`, `routes/user_routes.py:61`, `routes/user_routes.py:71`, `routes/user_routes.py:106`, `routes/user_routes.py:120`, `routes/user_routes.py:171-180`, `utils/helpers.py:21`, `utils/helpers.py:75`, `utils/helpers.py:110-111`
- **Description:** Várias regras e blocos aparecem copiados em mais de um lugar:
  - A regra de atraso (`if t.status != 'done' and t.status != 'cancelled'`) está reimplementada em 6 lugares, embora `Task.is_overdue()` já exista.
  - `get_tasks()` refaz à mão o `Task.to_dict()`.
  - A lista `['pending', 'in_progress', 'done', 'cancelled']` aparece 5 vezes, `['user', 'admin', 'manager']` 3 vezes e a regex de e-mail 3 vezes.
  - As contagens por status estão duplicadas entre `task_stats()` e `summary_report()`.
  - A conversão de tags (`','.join`) está repetida entre criar e atualizar uma task.
- **Impact:** Uma mudança de regra (por exemplo, um novo status) precisa ser feita em vários arquivos, e as cópias já divergem: `process_task_data` faz `strip()` no título, as rotas não fazem.
- **Recommendation:** Concentrar constantes, validadores e a regra de atraso no model `Task` e em um único módulo de validação, e reaproveitar os serializers. (Playbook T-13)

### [MEDIUM] Deprecated / Vulnerable Dependencies — unused packages
- **ID:** AP-18
- **File:** `requirements.txt:4`, `requirements.txt:5`, `requirements.txt:6`
- **Description:** Três pacotes declarados e nunca importados têm vulnerabilidades conhecidas:
  - `marshmallow==3.20.1`: CVE-2025-68480 (DoS em `Schema.load(many=True)`; corrigido em 3.26.2).
  - `requests==2.31.0`: CVE-2024-35195, CVE-2024-47081 e CVE-2026-25645 (corrigidos em 2.33.0).
  - `python-dotenv==1.0.0`: CVE-2026-28684 (`set_key` segue symlinks; corrigido em 1.2.2).
- **Impact:** Aumentam a superfície de ataque e o tempo de instalação sem trazer nenhum benefício, e disparam alertas de segurança.
- **Recommendation:** Remover `marshmallow` e `requests`. Se `python-dotenv` for usado para carregar `.env` na nova config, fixar `>=1.2.2`. (Playbook T-14, T-16)

### [MEDIUM] N+1 Queries and Per-Row Aggregation
- **ID:** AP-13
- **File:** `routes/report_routes.py:15-28`, `routes/report_routes.py:30-33`, `routes/report_routes.py:53-56`, `routes/report_routes.py:161-163`, `routes/task_routes.py:41-57`, `routes/task_routes.py:275-283`, `routes/user_routes.py:14-22`
- **Description:** Há consultas desnecessárias em vários endpoints:
  - `summary_report()` faz 12 `COUNT` separados (status e prioridade) em vez de um `GROUP BY`, carrega todas as tasks para contar as atrasadas e roda `Task.query.filter_by(user_id=u.id).all()` para cada usuário.
  - `get_tasks()` roda `User.query.get` e `Category.query.get` para cada task.
  - `get_categories()` faz um `COUNT` por categoria.
  - `get_users()` acessa `len(u.tasks)` com carregamento lazy.
  - `task_stats()` faz 5 contagens e ainda carrega todas as tasks.
- **Impact:** O número de queries cresce junto com o número de linhas, e as listagens e relatórios ficam lentos conforme a base cresce.
- **Recommendation:** Usar agregações com `GROUP BY`/`func.count`, carregamento antecipado (`selectinload`) ou lookups em lote, dentro de métodos de model. (Playbook T-08)

### [MEDIUM] Deprecated API — legacy `Query.get()`
- **ID:** AP-18
- **File:** `routes/report_routes.py:105`, `routes/report_routes.py:192`, `routes/report_routes.py:213`, `routes/task_routes.py:42`, `routes/task_routes.py:51`, `routes/task_routes.py:67`, `routes/task_routes.py:117`, `routes/task_routes.py:122`, `routes/task_routes.py:158`, `routes/task_routes.py:188`, `routes/task_routes.py:195`, `routes/task_routes.py:227`, `routes/user_routes.py:29`, `routes/user_routes.py:94`, `routes/user_routes.py:136`, `routes/user_routes.py:155`
- **Description:** O código usa `Model.query.get(id)`, API legada no SQLAlchemy 2.x (exigido pelo Flask-SQLAlchemy 3.1.1), que emite `LegacyAPIWarning`. Ela vem misturada com o restante da Query API legada (`Model.query.filter_by(...)`).
- **Impact:** Gera warnings em runtime, será removida em versões futuras e mantém o código preso a uma API em desuso.
- **Recommendation:** Trocar por `db.session.get(Model, id)` e `db.select(...)` dentro dos métodos de model. (Playbook T-14)

### [MEDIUM] Missing or Inconsistent Input Validation
- **ID:** AP-14
- **File:** `routes/report_routes.py:180`, `routes/report_routes.py:196-202`, `routes/task_routes.py:96-100`, `routes/task_routes.py:113`, `routes/task_routes.py:166-170`, `routes/task_routes.py:182`, `routes/task_routes.py:260-264`, `routes/user_routes.py:61`, `routes/user_routes.py:102-103`, `routes/user_routes.py:115`, `routes/user_routes.py:124-125`
- **Description:** Entradas comuns derrubam a API com HTTP 500, porque tipos e formatos não são verificados:
  - `priority < 1` com `"priority": "2"` gera `TypeError`.
  - `len(data['title'])` com `null` ou número também quebra.
  - `?priority=abc` em `int(priority)` gera `ValueError`.
  - `update_category()` testa `'name' in data` sem checar se `data` é `None`.
  - `re.match(..., email)` quebra com e-mail não-string.
  
  Outros campos passam sem nenhuma checagem: `color` (existe o `is_valid_color` sem uso), `name` vazio no update de usuário (vira 500 no commit) e `active` de qualquer tipo.
- **Impact:** Entradas inválidas comuns viram 500, e com `debug=True` a resposta é a página do debugger. Dados inconsistentes podem ser gravados.
- **Recommendation:** Criar validadores únicos por entidade, que checam tipo, faixa e formato e respondem 400 com a mensagem atual; usá-los igualmente no create e no update. (Playbook T-12)

### [MEDIUM] Swallowed Exceptions / No Centralized Error Handler
- **ID:** AP-15
- **File:** `routes/report_routes.py:186-188`, `routes/report_routes.py:207-209`, `routes/report_routes.py:221-223`, `routes/task_routes.py:62-63`, `routes/task_routes.py:137`, `routes/task_routes.py:151-154`, `routes/task_routes.py:204`, `routes/task_routes.py:221-223`, `routes/task_routes.py:236-238`, `routes/user_routes.py:87-90`, `routes/user_routes.py:130-132`, `routes/user_routes.py:149-151`, `utils/helpers.py:46`, `utils/helpers.py:49`, `utils/helpers.py:88`
- **Description:** Há 12 `except:` sem tipo e 3 `except Exception as e` que só imprimem ou ignoram o erro. Cada handler repete seu próprio `try`/`rollback`/`return 500`, e `get_tasks()` envolve a listagem inteira num `try` que devolve `'Erro interno'` sem registrar nada. Não existe `@app.errorhandler`, então 404/405 de rotas inexistentes e as exceções de AP-14 voltam como HTML, enquanto os handlers respondem com JSON `{'error': ...}`.
- **Impact:** Erros reais ficam escondidos (inclusive `KeyboardInterrupt`/`SystemExit` nos `except:` sem tipo), o formato das respostas de erro é inconsistente e há muito código repetido.
- **Recommendation:** Criar um middleware de erro centralizado (`errorhandler` para `HTTPException`, `SQLAlchemyError` e `Exception`, sempre com JSON `{'error': ...}` e log), capturar exceções específicas e remover os try/except repetidos. (Playbook T-07)

### [LOW] Dead Code and Unused Imports/Dependencies
- **ID:** AP-22
- **File:** `app.py:7`, `models/task.py:3`, `models/task.py:38-60`, `models/user.py:34-38`, `requirements.txt:4-6`, `routes/report_routes.py:7-8`, `routes/task_routes.py:7`, `routes/user_routes.py:6`, `services/notification_service.py:1-48`, `utils/helpers.py:3-7`, `utils/helpers.py:9-108`, `utils/helpers.py:110-116`
- **Description:** Muito código declarado não é usado em lugar nenhum:
  - Imports sem uso: `os, sys, json` (app), `json` (models/task), `json, os, sys, time` (task_routes), `hashlib, json` (user_routes), `format_date, calculate_percentage, json` (report_routes) e `os, json, sys, math, hashlib` (helpers).
  - `Task.validate_status`, `Task.validate_priority`, `Task.is_overdue` e `User.is_admin` nunca são chamados.
  - `NotificationService` nunca é instanciado; além disso, guarda notificações numa lista em memória (`self.notifications`, linha 6) que se perderia ao reiniciar.
  - Todas as funções e constantes de `utils/helpers.py` estão sem uso.
  - `marshmallow`, `requests` e `python-dotenv` são declarados e nunca importados.
- **Impact:** Ruído e falsa impressão de que existe camada de serviço e validação. O código morto guarda segredos (AP-01) e vulnerabilidades sem trazer benefício.
- **Recommendation:** Remover imports e dependências sem uso. Aproveitar as regras válidas (`is_overdue`, constantes) nas novas camadas e apagar o resto. (Playbook T-16)

### [LOW] Magic Numbers and Strings
- **ID:** AP-20
- **File:** `app.py:11`, `app.py:34`, `routes/report_routes.py:24-28`, `routes/report_routes.py:45`, `routes/report_routes.py:129`, `routes/report_routes.py:180`, `routes/task_routes.py:96`, `routes/task_routes.py:99`, `routes/task_routes.py:113`, `routes/task_routes.py:167`, `routes/task_routes.py:169`, `routes/task_routes.py:182`, `routes/user_routes.py:64`, `routes/user_routes.py:115`
- **Description:** Há literais soltos na lógica: limites de título `3`/`200`, faixa de prioridade `1`..`5`, senha mínima `4`, `timedelta(days=7)`, `t.priority <= 2` como "alta prioridade", prioridades 1–5 mapeadas para `critical..minimal`, `'#000000'`, a URI `'sqlite:///tasks.db'` e a porta `5000`. As constantes equivalentes (`MAX_TITLE_LENGTH` etc.) existem em `utils/helpers.py`, mas ninguém as usa.
- **Impact:** A regra fica implícita e fácil de alterar de forma inconsistente entre arquivos.
- **Recommendation:** Transformar os literais em constantes nomeadas no model ou em valores de config. (Playbook T-15)

### [LOW] Poor Naming
- **ID:** AP-21
- **File:** `models/category.py:14`, `models/task.py:45`, `routes/report_routes.py:24-28`, `routes/task_routes.py:242`, `routes/task_routes.py:247`
- **Description:** Alguns nomes não dizem o que guardam: `p1`..`p5` para contagens por prioridade, `d` e `p` como nomes de dicionário e parâmetro, e em `search_tasks()` a variável `query` guarda o termo de busca enquanto `tasks` guarda um objeto Query. O blueprint `report_bp` também registra as rotas de categorias.
- **Impact:** A leitura fica mais difícil e é fácil confundir o termo de busca com a query do ORM.
- **Recommendation:** Renomear internamente (`count_by_priority`, `search_term`, `task_query`) sem mexer nos campos da API. (Playbook T-15)

### [LOW] Verbose / Non-idiomatic Conditionals
- **ID:** AP-24
- **File:** `models/task.py:38-60`, `models/user.py:34-38`, `routes/task_routes.py:141`, `routes/task_routes.py:210`, `utils/helpers.py:21-23`, `utils/helpers.py:53-55`, `utils/helpers.py:103`
- **Description:** Há vários `if cond: return True else: return False`, a pirâmide de 3 níveis em `is_overdue()`, comparações como `p >= 1 and p <= 5` e `type(tags) == list` em vez de `isinstance`.
- **Impact:** A leitura fica mais difícil e `type() ==` não aceita subclasses.
- **Recommendation:** Retornar a expressão booleana direto, usar comparação encadeada (`1 <= p <= 5`) e `isinstance`. (Playbook T-16)

### [LOW] print Logging Instead of a Logger
- **ID:** AP-23
- **File:** `routes/task_routes.py:149`, `routes/task_routes.py:153`, `routes/task_routes.py:219`, `routes/task_routes.py:234`, `routes/user_routes.py:83`, `routes/user_routes.py:147`, `services/notification_service.py:21`, `services/notification_service.py:24`, `utils/helpers.py:39`, `utils/helpers.py:41`
- **Description:** Os handlers e helpers registram eventos com `print()` (`"Task criada: ..."`, `"Usuário deletado: ..."`, `"Email enviado para {to}"`), sem nível de log nem configuração. O `print` de `user_routes.py:89`, que vaza dados sensíveis, está em AP-04. Os `print` do `seed.py` são saída de CLI e não entram aqui.
- **Impact:** Não dá para filtrar ou desligar logs por nível nem mandá-los para outro destino, e e-mails (PII) acabam no stdout.
- **Recommendation:** Usar `logging.getLogger(__name__)` com nível configurável. (Playbook T-16)

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `models/category.py:11`, `models/task.py:15-16`, `models/task.py:52`, `models/user.py:14`, `routes/report_routes.py:35`, `routes/report_routes.py:42`, `routes/report_routes.py:45`, `routes/report_routes.py:71`, `routes/report_routes.py:133`, `routes/task_routes.py:31`, `routes/task_routes.py:72`, `routes/task_routes.py:215`, `routes/task_routes.py:285`, `routes/user_routes.py:172`, `seed.py:66`, `seed.py:67`, `seed.py:69`, `seed.py:70`, `seed.py:74`, `services/notification_service.py:35`, `utils/helpers.py:38` | `datetime.utcnow()`: deprecated desde o Python 3.12 (runtime local 3.14.7) | `datetime.now(timezone.utc)` |
| `routes/report_routes.py:105`, `routes/report_routes.py:192`, `routes/report_routes.py:213`, `routes/task_routes.py:42`, `routes/task_routes.py:51`, `routes/task_routes.py:67`, `routes/task_routes.py:117`, `routes/task_routes.py:122`, `routes/task_routes.py:158`, `routes/task_routes.py:188`, `routes/task_routes.py:195`, `routes/task_routes.py:227`, `routes/user_routes.py:29`, `routes/user_routes.py:94`, `routes/user_routes.py:136`, `routes/user_routes.py:155` | `Model.query.get(id)`: Query API legada do SQLAlchemy 2.x (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `requirements.txt:1` | flask@3.0.0: CVE-2026-27205 | `flask>=3.1.3` |
| `requirements.txt:3` | flask-cors@4.0.0: CVE-2024-1681, CVE-2024-6221, CVE-2024-6844, CVE-2024-6866, CVE-2024-6839 | `flask-cors>=6.0.0` |
| `requirements.txt:4` | marshmallow@3.20.1: CVE-2025-68480 (não usado) | remover (ou `>=3.26.2`) |
| `requirements.txt:5` | requests@2.31.0: CVE-2024-35195, CVE-2024-47081, CVE-2026-25645 (não usado) | remover (ou `>=2.33.0`) |
| `requirements.txt:6` | python-dotenv@1.0.0: CVE-2026-28684 (não usado) | `python-dotenv>=1.2.2` se adotado na config, senão remover |

```text
================================
Total: 21 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
