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
| `SECRET_KEY` | valor aleatório efêmero | Chave de assinatura do Flask e dos tokens de login |
| `TOKEN_MAX_AGE_SECONDS` | `28800` (8 h) | Validade do token devolvido pelo `POST /login` |
| `HOST` | `127.0.0.1` | Interface de escuta (use `0.0.0.0` em containers) |
| `PORT` | `5000` | Porta HTTP |
| `FLASK_DEBUG` | `false` | Liga o modo debug (nunca em produção) |
| `APP_ENV` | `producao` | Nome do ambiente exibido no `/health` |
| `DATABASE_PATH` | `loja.db` | Arquivo do banco SQLite |
| `SEED_DATABASE` | `true` | Insere produtos e usuários de demonstração quando o banco está vazio |
| `SEED_PASSWORD` | senha aleatória por boot | Senha dos usuários de demonstração (registrada no log quando sorteada) |
| `LOG_LEVEL` | `INFO` | Nível dos logs da aplicação |
| `CORS_ORIGINS` | `http://<HOST>:<PORT>` | Origens permitidas, separadas por vírgula (`*` libera todas — só em desenvolvimento) |
| `ADMIN_ENDPOINTS_ENABLED` | `false` | Habilita `/admin/reset-db` e `/admin/query` |
| `ADMIN_TOKEN` | — | Token exigido no header `X-Admin-Token` pelos endpoints `/admin/*` |

Com os endpoints administrativos habilitados, `/admin/query` aceita apenas uma única consulta `SELECT`, executada numa conexão somente leitura. Consultas que citam colunas de credenciais (`senha`, `password`, `token`, `secret`) são recusadas e, na execução, um authorizer do SQLite troca toda leitura dessas colunas por `NULL` — então nem `SELECT *`, aliases, subconsultas ou `UNION` expõem hashes de senha.

## Autenticação

`POST /login` devolve, junto com os dados do usuário, um `token` assinado com `SECRET_KEY` e com validade de `TOKEN_MAX_AGE_SECONDS`. Envie-o nas rotas de gestão:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login -H 'Content-Type: application/json' \
  -d '{"email": "admin@loja.com", "senha": "<SEED_PASSWORD>"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)["dados"]["token"])')
curl -s http://127.0.0.1:5000/relatorios/vendas -H "Authorization: Bearer $TOKEN"
```

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`, `POST /usuarios`, `POST /login`, `POST /pedidos` |
| Administrador (`tipo = admin`) | `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas` |
| O próprio usuário ou administrador | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` |
| `X-Admin-Token` + `ADMIN_ENDPOINTS_ENABLED=true` | `POST /admin/reset-db`, `POST /admin/query` |

Sem token, com token adulterado ou expirado a resposta é `401`; com token válido de um usuário sem permissão, `403`. O papel é lido do banco a cada requisição (o token carrega apenas o id do usuário).

## Regras de pedido

- Criar um pedido baixa o estoque dos produtos na mesma transação.
- Mudar o status para `cancelado` devolve ao estoque as quantidades dos itens, uma única vez.
- `cancelado` e `entregue` são estados finais: tentar sair deles responde 400. Repetir o status atual não altera nada.

## Estrutura

```text
app.py              # ponto de entrada (python app.py)
src/app.py          # create_app(): composition root
src/config/         # settings a partir de variáveis de ambiente
src/models/         # conexão, schema/seed e acesso a dados por entidade
src/services/       # casos de uso de pedido, notificações e token de login
src/controllers/    # fluxo das requisições e validação de entrada
src/views/          # rotas (blueprints), conversores de URL e serializers
src/middlewares/    # error handler central, guards de autenticação/papel e dos endpoints administrativos
src/utils/          # hierarquia de erros
```
