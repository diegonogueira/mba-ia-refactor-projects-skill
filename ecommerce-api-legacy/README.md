# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://127.0.0.1:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.

## Configuração

Tudo é lido de variáveis de ambiente (veja `.env.example`; nada carrega esse arquivo automaticamente, exporte as variáveis antes do `npm start`):

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `HOST` | `127.0.0.1` | Interface de rede (`0.0.0.0` em containers) |
| `DATABASE_PATH` | `:memory:` | Banco SQLite |
| `ADMIN_TOKEN` | *(vazio)* | Quando definido, `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `X-Admin-Token`; sem valor, essas rotas ficam públicas |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug` |

```bash
ADMIN_TOKEN="$(openssl rand -hex 32)" HOST=0.0.0.0 npm start
```

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
