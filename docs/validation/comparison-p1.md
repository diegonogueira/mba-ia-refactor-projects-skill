| # | Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|---|
| 1 | GET | `/` | 200 | 200 | igual |
| 2 | GET | `/health` | 200 | 200 | DIFERENTE (esperado: GET /health sem secret_key, debug e db_path (exceção 1: dados sensíveis)): shape (-db_path, -debug, -secret_key) |
| 3 | GET | `/produtos` | 200 | 200 | igual |
| 4 | GET | `/produtos/busca?q=Mouse` | 200 | 200 | igual |
| 5 | GET | `/produtos/busca?categoria=informatica&preco_min=50&preco_max=300` | 200 | 200 | igual |
| 6 | GET | `/produtos/busca?q=%27%20OR%20%271%27%3D%271` | 200 | 200 | DIFERENTE (esperado: busca com payload de SQL injection passa a retornar lista vazia (queries parametrizadas)): shape (dados: lista vazia) |
| 7 | GET | `/produtos/1` | 200 | 200 | igual |
| 8 | GET | `/produtos/9999` | 404 | 404 | igual |
| 9 | POST | `/produtos` | 201 | 201 | igual |
| 10 | POST | `/produtos` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 11 | POST | `/produtos` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 12 | POST | `/produtos` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 13 | POST | `/produtos` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 14 | PUT | `/produtos/2` | 200 | 200 | igual |
| 15 | PUT | `/produtos/9999` | 404 | 404 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 16 | DELETE | `/produtos/11` | 200 | 200 | igual |
| 17 | DELETE | `/produtos/9999` | 404 | 404 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 18 | GET | `/usuarios` | 200 | 200 | igual |
| 19 | GET | `/usuarios/1` | 200 | 200 | DIFERENTE (esperado: usuário sem o campo senha (exceção 1: dados sensíveis)): shape (-dados.senha) |
| 20 | GET | `/usuarios/9999` | 404 | 404 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 21 | POST | `/usuarios` | 201 | 201 | igual |
| 22 | POST | `/usuarios` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 23 | POST | `/login` | 200 | 200 | igual |
| 24 | POST | `/login` | 401 | 401 | igual |
| 25 | POST | `/login` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 26 | POST | `/pedidos` | 201 | 201 | igual |
| 27 | POST | `/pedidos` | 400 | 400 | igual |
| 28 | POST | `/pedidos` | 400 | 400 | igual |
| 29 | POST | `/pedidos` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 30 | GET | `/pedidos` | 200 | 200 | igual |
| 31 | GET | `/pedidos/usuario/2` | 200 | 200 | igual |
| 32 | PUT | `/pedidos/1/status` | 200 | 200 | igual |
| 33 | PUT | `/pedidos/1/status` | 400 | 400 | DIFERENTE (esperado: erro agora inclui "sucesso": false (envelope de erro padronizado)): shape (+sucesso) |
| 34 | GET | `/relatorios/vendas` | 200 | 200 | igual |
| 35 | POST | `/admin/query` | 200 | 403 | DIFERENTE (esperado: POST /admin/query desabilitado por padrão → 403 (exceção 2: endpoint destrutivo)): status 200 → 403; shape (-dados, +erro) |
| 36 | POST | `/admin/reset-db` | 200 | 403 | DIFERENTE (esperado: POST /admin/reset-db desabilitado por padrão → 403 (exceção 2: endpoint destrutivo)): status 200 → 403; shape (-mensagem, +erro) |

20/36 checks idênticos (status + shape); 16 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
