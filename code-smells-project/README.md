# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em camadas MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (as senhas do seed são gravadas como hash).

## Configuração

Todas as configurações vêm de variáveis de ambiente; veja `.env.example` (o arquivo não é carregado automaticamente — exporte as variáveis no shell ou no ambiente de execução).

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | valor aleatório efêmero | Chave de assinatura do Flask |
| `HOST` | `127.0.0.1` | Interface de escuta (use `0.0.0.0` em containers) |
| `PORT` | `5000` | Porta HTTP |
| `FLASK_DEBUG` | `false` | Liga o modo debug (nunca em produção) |
| `APP_ENV` | `producao` | Nome do ambiente exibido no `/health` |
| `DATABASE_PATH` | `loja.db` | Arquivo do banco SQLite |
| `SEED_DATABASE` | `true` | Insere produtos e usuários de demonstração quando o banco está vazio |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Habilita `/admin/reset-db` e `/admin/query` |
| `ADMIN_TOKEN` | — | Token exigido no header `X-Admin-Token` pelos endpoints `/admin/*` |

Com os endpoints administrativos habilitados, `/admin/query` aceita apenas uma única consulta `SELECT`, executada numa conexão somente leitura.

## Estrutura

```text
app.py              # ponto de entrada (python app.py)
src/app.py          # create_app(): composition root
src/config/         # settings a partir de variáveis de ambiente
src/models/         # conexão, schema/seed e acesso a dados por entidade
src/services/       # casos de uso de pedido e notificações
src/controllers/    # fluxo das requisições e validação de entrada
src/views/          # rotas (blueprints) e serializers
src/middlewares/    # error handler central e guard dos endpoints administrativos
src/utils/          # hierarquia de erros
```
