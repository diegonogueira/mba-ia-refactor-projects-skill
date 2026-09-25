# task-manager-api

API de Task Manager em Python/Flask, organizada em MVC: **Models** (dados e regras de domínio),
**Views** (rotas e serializers) e **Controllers** (fluxo da requisição), com `config`, `services`,
`middlewares` e `utils` de apoio.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env    # opcional: ajuste SECRET_KEY, porta, CORS etc.
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com
usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints
vão retornar listas vazias.

Os usuários de exemplo **não têm senha fixa no código**: defina `SEED_PASSWORD` antes de rodar o seed ou
anote a senha sorteada que o script mostra uma única vez na saída.

## Configuração

Todas as configurações vêm de variáveis de ambiente (veja `.env.example`); um arquivo `.env` na raiz é
carregado automaticamente. Nenhum segredo fica no código: sem `SECRET_KEY` definida, a aplicação gera um
valor efêmero a cada boot e registra um aviso.

| Variável | Default | Descrição |
|---|---|---|
| `SECRET_KEY` | efêmera | Chave usada para assinar os tokens de login (efêmera = tokens caem a cada boot) |
| `TOKEN_MAX_AGE` | `28800` | Validade, em segundos, do token devolvido por `POST /login` |
| `DATABASE_URL` | `sqlite:///tasks.db` | Banco de dados (SQLite relativo fica em `instance/`) |
| `HOST` | `127.0.0.1` | Interface do servidor (use `0.0.0.0` para expor na rede) |
| `PORT` | `5000` | Porta do servidor |
| `FLASK_DEBUG` | `false` | Modo debug do Flask |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Origens liberadas no CORS, separadas por vírgula (`*` libera todas — só em desenvolvimento) |
| `LOG_LEVEL` | `INFO` | Nível dos logs |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Libera os endpoints administrativos (junto com `ADMIN_TOKEN`) |
| `ADMIN_TOKEN` | vazio | Token esperado no header `X-Admin-Token` dos endpoints administrativos |
| `SEED_PASSWORD` | sorteada | Senha dos usuários criados pelo `seed.py` (mínimo 8 caracteres) |

## Estrutura

```text
app.py                  # entrada: cria a app pela factory e sobe o servidor
seed.py                 # popula o banco com os dados de exemplo
src/
├── app.py              # composition root: create_app()
├── config/settings.py  # configurações lidas do ambiente
├── models/             # entidades, consultas e regras de domínio
├── services/           # autenticação e relatórios (casos de uso)
├── controllers/        # fluxo da requisição + validadores de payload
├── views/              # blueprints (URL → controller) e serializers
├── middlewares/        # erros centralizados, guards de autenticação (token + papel) e guard administrativo
└── utils/              # erros, validadores e helpers sem dependência de framework
```

## Endpoints

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| GET | `/` | Identificação da API | público |
| GET | `/health` | Health check | público |
| GET | `/tasks` | Lista tasks (com nome do usuário e da categoria) | público |
| POST | `/tasks` | Cria uma task | autenticado; `user_id` = o próprio (ou admin) |
| GET | `/tasks/search` | Busca por `q`, `status`, `priority`, `user_id` | público |
| GET | `/tasks/stats` | Estatísticas das tasks | público |
| GET | `/tasks/<id>` | Detalha uma task | público |
| PUT/DELETE | `/tasks/<id>` | Atualiza e remove uma task | autenticado; dono da task (ou admin) |
| GET | `/users` | Lista usuários com total de tasks | admin |
| POST | `/users` | Cria um usuário (cadastro) | público |
| GET/PUT | `/users/<id>` | Detalha e atualiza um usuário | o próprio usuário (ou admin) |
| DELETE | `/users/<id>` | Remove um usuário e as tasks dele | **endpoint administrativo** (ver abaixo) |
| GET | `/users/<id>/tasks` | Tasks de um usuário | o próprio usuário (ou admin) |
| POST | `/login` | Autentica e devolve um token assinado | público |
| GET | `/reports/summary` | Relatório geral | admin |
| GET | `/reports/user/<id>` | Relatório de um usuário | o próprio usuário (ou admin) |
| GET | `/categories` | Lista categorias com total de tasks | público |
| POST | `/categories` | Cria uma categoria | admin |
| PUT/DELETE | `/categories/<id>` | Atualiza e remove uma categoria | admin |

Todas as respostas, inclusive as de erro, são JSON. Erros usam o envelope `{"error": "mensagem"}`.

## Autenticação

1. Faça login: `POST /login` com `{"email": "...", "password": "..."}`. A resposta traz o campo `token`.
2. Envie o token nas rotas protegidas: `Authorization: Bearer <token>`.

```bash
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email": "joao@email.com", "password": "<SEED_PASSWORD>"}' | python -c 'import sys, json; print(json.load(sys.stdin)["token"])')
curl -s localhost:5000/users -H "Authorization: Bearer $TOKEN"
```

- O token é assinado com `SECRET_KEY`, expira após `TOKEN_MAX_AGE` segundos e carrega só o id do usuário; o
  papel é lido do banco a cada requisição (rebaixar ou desativar um usuário vale imediatamente).
- Sem token, com token adulterado ou expirado → **401** (`WWW-Authenticate: Bearer`); token válido sem
  permissão para a rota → **403**; usuário inativo → **403**.
- Tasks com dono só são alteradas/removidas pelo dono ou por um admin; tasks sem `user_id` são do time e
  qualquer usuário autenticado pode editá-las. Criar ou reatribuir uma task para outro usuário exige ser admin.
- No seed, `joao@email.com` é o admin; `maria@email.com` é um usuário comum.

## Regras de segurança dos endpoints de usuário

- `POST /users` é o cadastro público e cria sempre com `role: "user"`. Pedir `admin` ou `manager` devolve **403**.
- `PUT /users/<id>` edita o perfil (nome, e-mail, senha) e não altera `role` nem `active`: ambos devolvem **403**.
- Senhas têm no mínimo 8 caracteres e são gravadas com hash `scrypt` (Werkzeug).
- `name`, `email`, `description`, `color` e `tags` são validados contra os limites das colunas; nomes não podem
  ser vazios nem só espaços (na criação e na atualização); `color` precisa ser hexadecimal no formato `#RRGGBB`.
- `DELETE /users/<id>` apaga o usuário **e todas as tasks dele**. Por ser destrutivo, ele nasce **fechado**:
  responde **403** até que `ADMIN_ENDPOINTS_ENABLED=true` e `ADMIN_TOKEN` estejam definidos e a requisição
  traga o header `X-Admin-Token` correspondente.
- Falhas de gravação são registradas apenas pelo tipo do erro, e o SQLAlchemy roda com
  `hide_parameters`: nenhum hash de senha chega aos logs.
