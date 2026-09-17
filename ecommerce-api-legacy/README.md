# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

Requer Node.js >= 20.17 (exigência do `sqlite3@6`).

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. Por padrão o banco SQLite é em memória e já carrega seeds automaticamente no boot.

O `package.json` autoriza o script de instalação do `sqlite3` (`allowScripts`), necessário para o binário nativo nas versões recentes do npm.

Exemplos de requisições estão em `api.http`.

## Configuração

Todas as configurações vêm de variáveis de ambiente (veja `.env.example`):

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `DATABASE_PATH` | `:memory:` | Caminho do banco SQLite; com um arquivo, schema e seed são criados só no primeiro boot |
| `PAYMENT_GATEWAY_KEY` | — | Chave do gateway de pagamento (o gateway atual é simulado) |
| `ADMIN_TOKEN` | — | Quando definido, `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `X-Admin-Token` |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug` |

Exemplo: `ADMIN_TOKEN=troque-me PAYMENT_GATEWAY_KEY=pk_test_xxx npm start`

## Estrutura

```text
src/
├── app.js            # entry point: carrega config, inicializa o banco e sobe o servidor
├── createApp.js      # composition root: conecta models, services, controllers e rotas
├── config/           # settings a partir de variáveis de ambiente
├── models/           # conexão SQLite (promises + transações), schema/seed e acesso a dados por entidade
├── services/         # casos de uso: checkout, relatório financeiro, exclusão de usuário, gateway de pagamento
├── controllers/      # fluxo HTTP: valida entrada, chama services, escolhe status e view
├── views/            # rotas (URL → controller) e serializers das respostas
├── middlewares/      # tratamento central de erros, async handler, guard de admin
└── utils/            # erros da aplicação, validação, hash de senha, logger
```
