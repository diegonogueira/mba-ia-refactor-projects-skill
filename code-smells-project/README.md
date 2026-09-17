# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em camadas MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (desative com `SEED_DATABASE=false`).

## Configuração

Todas as opções vêm de variáveis de ambiente (veja `.env.example`; o arquivo não é carregado automaticamente — exporte as variáveis no shell):

| Variável | Default | Descrição |
|---|---|---|
| `SECRET_KEY` | valor aleatório por boot (com aviso no log) | Chave de assinatura do Flask |
| `FLASK_DEBUG` | `false` | Modo debug (nunca habilite exposto na rede) |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | Endereço do servidor |
| `DATABASE_PATH` | `loja.db` | Arquivo SQLite |
| `SEED_DATABASE` | `true` | Insere dados de demonstração quando o banco está vazio |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula |
| `APP_ENV` | `producao` | Nome do ambiente exibido em `/health` |
| `ADMIN_ENDPOINTS_ENABLED` / `ADMIN_TOKEN` | `false` / vazio | Habilitam `/admin/*` (header `X-Admin-Token`) |
| `LOG_LEVEL` | `INFO` | Nível de log |

## Endpoints administrativos

`POST /admin/reset-db` e `POST /admin/query` respondem `403` por padrão. Para habilitar:

```bash
ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=um-token-longo python app.py
curl -X POST localhost:5000/admin/query -H 'X-Admin-Token: um-token-longo' \
     -H 'Content-Type: application/json' -d '{"sql": "SELECT COUNT(*) AS total FROM produtos"}'
```

`/admin/query` aceita apenas uma única consulta `SELECT`, executada numa conexão somente leitura.

## Estrutura

```text
app.py                  # entry point (python app.py)
src/app.py              # composition root: create_app()
src/config/             # settings a partir de variáveis de ambiente, logging
src/models/             # conexão SQLite, schema, seed e acesso a dados por entidade
src/services/           # casos de uso (criação de pedido) e notificações
src/controllers/        # fluxo da requisição: entrada → validação → model/service → resposta
src/views/              # blueprints (URL → controller) e serializers
src/middlewares/        # tratamento centralizado de erros e guard dos endpoints admin
src/utils/              # erros da aplicação e validadores genéricos
```
