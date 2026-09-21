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
| `SECRET_KEY` | efêmera | Chave usada para assinar os tokens de login |
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
├── middlewares/        # tratamento de erros centralizado e guard administrativo
└── utils/              # erros, validadores e helpers sem dependência de framework
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Identificação da API |
| GET | `/health` | Health check |
| GET | `/tasks` | Lista tasks (com nome do usuário e da categoria) |
| POST | `/tasks` | Cria uma task |
| GET | `/tasks/search` | Busca por `q`, `status`, `priority`, `user_id` |
| GET | `/tasks/stats` | Estatísticas das tasks |
| GET/PUT/DELETE | `/tasks/<id>` | Detalha, atualiza e remove uma task |
| GET | `/users` | Lista usuários com total de tasks |
| POST | `/users` | Cria um usuário |
| GET/PUT | `/users/<id>` | Detalha e atualiza um usuário |
| DELETE | `/users/<id>` | Remove um usuário e as tasks dele — **endpoint administrativo** (ver abaixo) |
| GET | `/users/<id>/tasks` | Tasks de um usuário |
| POST | `/login` | Autentica e devolve um token assinado |
| GET | `/reports/summary` | Relatório geral |
| GET | `/reports/user/<id>` | Relatório de um usuário |
| GET | `/categories` | Lista categorias com total de tasks |
| POST | `/categories` | Cria uma categoria |
| PUT/DELETE | `/categories/<id>` | Atualiza e remove uma categoria |

Todas as respostas, inclusive as de erro, são JSON. Erros usam o envelope `{"error": "mensagem"}`.

## Regras de segurança dos endpoints de usuário

A API ainda não exige autenticação (veja as limitações abaixo), então os endpoints públicos não concedem
privilégios a quem chama:

- `POST /users` cria sempre com `role: "user"`. Pedir `admin` ou `manager` devolve **403**.
- `PUT /users/<id>` não altera `role` nem `active`: ambos devolvem **403**. Esses campos só devem mudar
  por uma rota administrativa autenticada.
- Senhas têm no mínimo 8 caracteres e são gravadas com hash `scrypt` (Werkzeug).
- `name`, `email`, `description`, `color` e `tags` são validados contra os limites das colunas; `color`
  precisa ser hexadecimal no formato `#RRGGBB`.
- `DELETE /users/<id>` apaga o usuário **e todas as tasks dele**. Por ser destrutivo e não haver
  autenticação, ele nasce **fechado**: responde **403** até que `ADMIN_ENDPOINTS_ENABLED=true` e
  `ADMIN_TOKEN` estejam definidos e a requisição traga o header `X-Admin-Token` correspondente.
- Falhas de gravação são registradas apenas pelo tipo do erro, e o SQLAlchemy roda com
  `hide_parameters`: nenhum hash de senha chega aos logs.

**Limitação conhecida:** nenhuma rota exige autenticação. O token devolvido por `POST /login` é assinado,
mas ainda não é verificado por nenhum endpoint — qualquer cliente com acesso de rede consegue ler, alterar
e apagar dados. Antes de expor a API fora do ambiente local, adicione um middleware que valide esse token
(e o papel do usuário) nas rotas de escrita.
