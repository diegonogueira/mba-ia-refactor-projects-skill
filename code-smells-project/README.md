# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em camadas MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo.

Os usuários de demonstração **não têm senha fixa no código**: defina `SEED_PASSWORD` para escolher a senha ou deixe em branco para que uma senha aleatória seja sorteada no primeiro boot e registrada no log uma única vez (procure por `SEED_PASSWORD não definido` na saída). Use `SEED_DATABASE=false` para não criá-los.

## Configuração

Todas as configurações vêm de variáveis de ambiente; veja `.env.example` (o arquivo não é carregado automaticamente — exporte as variáveis no shell ou no ambiente de execução).

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | valor aleatório efêmero | Chave que assina os tokens do `/login` (sem ela, os tokens deixam de valer a cada reinício) |
| `TOKEN_MAX_AGE` | `28800` | Validade do token de login, em segundos |
| `HOST` | `127.0.0.1` | Interface de escuta (use `0.0.0.0` em containers) |
| `PORT` | `5000` | Porta HTTP |
| `FLASK_DEBUG` | `false` | Liga o modo debug (nunca em produção) |
| `APP_ENV` | `producao` | Nome do ambiente exibido no `/health` |
| `DATABASE_PATH` | `loja.db` | Arquivo do banco SQLite |
| `SEED_DATABASE` | `true` | Insere produtos e usuários de demonstração quando o banco está vazio |
| `SEED_PASSWORD` | senha aleatória por boot | Senha dos usuários de demonstração (registrada no log quando sorteada) |
| `LOG_LEVEL` | `INFO` | Nível dos logs da aplicação |
| `CORS_ORIGINS` | `http://HOST:PORT` | Origens permitidas, separadas por vírgula (`*` libera todas — só em desenvolvimento) |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Habilita `/admin/reset-db` e `/admin/query` |
| `ADMIN_TOKEN` | — | Token exigido no header `X-Admin-Token` pelos endpoints `/admin/*` |

## Autenticação

`POST /login` devolve, além dos dados do usuário, um `token` assinado. Envie-o como `Authorization: Bearer <token>` nas rotas que expõem dados de terceiros ou apagam dados — sem ele, respondem `403`:

| Rota | Quem acessa |
|---|---|
| `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `DELETE /produtos/<id>` | usuários do tipo `admin` |
| `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` | o próprio usuário ou um `admin` |

As demais rotas continuam públicas.

## Pedidos

Cancelar um pedido (`PUT /pedidos/<id>/status` com `"cancelado"`) devolve ao estoque as quantidades dos itens, uma única vez. `cancelado` e `entregue` são estados finais: tentar sair deles responde `400`; repetir o status atual não altera nada.

## Endpoints administrativos

Com os endpoints administrativos habilitados, `/admin/query` aceita apenas uma única consulta `SELECT`, executada numa conexão somente leitura. Um *authorizer* do SQLite permite só leituras e faz as colunas de credenciais (`senha`, `password`, `token`, `secret`) serem lidas como `NULL` em qualquer forma de consulta (aliases, subconsultas, `UNION`) — hashes de senha não saem por essa rota. Consultas que citam essas colunas pelo nome são recusadas.

## Estrutura

```text
app.py              # ponto de entrada (python app.py)
src/app.py          # create_app(): composition root
src/config/         # settings a partir de variáveis de ambiente
src/models/         # conexão, schema/seed e acesso a dados por entidade
src/services/       # casos de uso de pedido e notificações
src/controllers/    # fluxo das requisições e validação de entrada
src/views/          # rotas (blueprints) e serializers
src/middlewares/    # error handler central, guards de admin/dono e dos endpoints administrativos
src/utils/          # hierarquia de erros
```

Convenção de nomes: infraestrutura (`config/`, `models/database.py`, `middlewares/`, `utils/`) usa identificadores em inglês; o domínio (models, services, controllers, views) usa português.
