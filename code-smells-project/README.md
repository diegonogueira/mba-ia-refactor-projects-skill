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
| `SECRET_KEY` | valor aleatório efêmero | Chave de assinatura do Flask |
| `HOST` | `127.0.0.1` | Interface de escuta (use `0.0.0.0` em containers) |
| `PORT` | `5000` | Porta HTTP |
| `FLASK_DEBUG` | `false` | Liga o modo debug (nunca em produção) |
| `APP_ENV` | `producao` | Nome do ambiente exibido no `/health` |
| `DATABASE_PATH` | `loja.db` | Arquivo do banco SQLite |
| `SEED_DATABASE` | `true` | Insere produtos e usuários de demonstração quando o banco está vazio |
| `SEED_PASSWORD` | senha aleatória por boot | Senha dos usuários de demonstração (registrada no log quando sorteada) |
| `LOG_LEVEL` | `INFO` | Nível dos logs da aplicação |
| `CORS_ORIGINS` | `http://127.0.0.1:5000` | Origens permitidas, separadas por vírgula (`*` libera todas — só em desenvolvimento) |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Habilita `/admin/reset-db` e `/admin/query` |
| `ADMIN_TOKEN` | — | Token exigido no header `X-Admin-Token` pelos endpoints `/admin/*` |

Com os endpoints administrativos habilitados, `/admin/query` aceita apenas uma única consulta `SELECT`, executada numa conexão somente leitura. Consultas que citam colunas de credenciais (`senha`, `password`, `token`, `secret`) são recusadas e esses campos também são removidos das linhas retornadas — então nem `SELECT *` expõe hashes de senha.

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
