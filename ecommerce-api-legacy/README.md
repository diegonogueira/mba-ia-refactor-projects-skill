# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://127.0.0.1:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

As rotas administrativas (`GET /api/admin/financial-report` e `DELETE /api/users/:id`) são **fechadas por padrão**: respondem `403` até serem habilitadas por configuração.

```bash
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN="$(openssl rand -hex 32)" npm start
```

Exemplos de requisições estão em `api.http`.

## Configuração

Tudo é lido de variáveis de ambiente (veja `.env.example`; nada carrega esse arquivo automaticamente, exporte as variáveis antes do `npm start`):

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `HOST` | `127.0.0.1` | Interface de rede (`0.0.0.0` em containers) |
| `DATABASE_PATH` | `:memory:` | Banco SQLite |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Habilita as rotas administrativas; enquanto for falso, elas respondem `403` |
| `ADMIN_TOKEN` | *(vazio)* | Token exigido no header `X-Admin-Token` das rotas administrativas; sem ele as rotas seguem fechadas |
| `SEED_USER_PASSWORD` | *(vazio)* | Senha do usuário de seed; sem valor o seed gera uma senha aleatória |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug` |

## Estrutura

```text
src/
├── app.js            # entry point: configuração, banco, schema/seed e listen
├── createApp.js      # composition root: monta models, services, controllers e rotas
├── config/           # settings lidos do ambiente
├── models/           # conexão SQLite, schema/seed e acesso a dados por entidade
├── services/         # casos de uso com várias entidades (checkout, exclusão de usuário) e gateway de pagamento
├── controllers/      # fluxo da requisição: valida, chama service/model, responde
├── views/            # rotas (URL → controller) e presenters das respostas
├── middlewares/      # tratamento de erros, guarda de admin, async handler
└── utils/            # erros, constantes, logger, hash de senha e validadores
```

## Regras de negócio relevantes

- Um usuário não pode se matricular duas vezes no mesmo curso: o segundo `POST /api/checkout` com o mesmo `eml` e `c_id` responde `400` e o cartão não é cobrado.
- Se a gravação da matrícula falhar depois da autorização do pagamento, a autorização é estornada e o estorno fica registrado em `audit_logs`.
- `DELETE /api/users/:id` responde `400` para um id inválido e `404` quando não existe usuário com aquele id.
