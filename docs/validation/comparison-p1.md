| Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|
| GET | `/` | 200 | 200 | igual |
| GET | `/health` | 200 | 200 | DIFERENTE: shape (-db_path, -debug, -secret_key) |
| GET | `/produtos` | 200 | 200 | igual |
| GET | `/produtos/busca?q=Mouse` | 200 | 200 | igual |
| GET | `/produtos/busca?categoria=informatica&preco_min=50&preco_max=300` | 200 | 200 | igual |
| GET | `/produtos/busca?q=%27%20OR%20%271%27%3D%271` | 200 | 200 | DIFERENTE: shape (dados: lista vazia) |
| GET | `/produtos/1` | 200 | 200 | igual |
| GET | `/produtos/9999` | 404 | 404 | igual |
| POST | `/produtos` | 201 | 201 | igual |
| POST | `/produtos` | 400 | 400 | igual |
| POST | `/produtos` | 400 | 400 | igual |
| POST | `/produtos` | 400 | 400 | igual |
| POST | `/produtos` | 400 | 400 | igual |
| PUT | `/produtos/2` | 200 | 200 | igual |
| PUT | `/produtos/9999` | 404 | 404 | igual |
| DELETE | `/produtos/11` | 200 | 200 | igual |
| DELETE | `/produtos/9999` | 404 | 404 | igual |
| GET | `/usuarios` | 200 | 200 | igual |
| GET | `/usuarios/1` | 200 | 200 | DIFERENTE: shape (-dados.senha) |
| GET | `/usuarios/9999` | 404 | 404 | igual |
| POST | `/usuarios` | 201 | 201 | igual |
| POST | `/usuarios` | 400 | 400 | igual |
| POST | `/login` | 200 | 200 | igual |
| POST | `/login` | 401 | 401 | igual |
| POST | `/login` | 400 | 400 | igual |
| POST | `/pedidos` | 201 | 201 | igual |
| POST | `/pedidos` | 400 | 400 | igual |
| POST | `/pedidos` | 400 | 400 | igual |
| POST | `/pedidos` | 400 | 400 | igual |
| GET | `/pedidos` | 200 | 200 | igual |
| GET | `/pedidos/usuario/2` | 200 | 200 | igual |
| PUT | `/pedidos/1/status` | 200 | 200 | igual |
| PUT | `/pedidos/1/status` | 400 | 400 | igual |
| GET | `/relatorios/vendas` | 200 | 200 | igual |
| POST | `/admin/query` | 200 | 403 | DIFERENTE: status 200 → 403; shape (-dados, -sucesso, +erro) |
| POST | `/admin/reset-db` | 200 | 403 | DIFERENTE: status 200 → 403; shape (-mensagem, -sucesso, +erro) |

31/36 checks idênticos (status + shape); 5 diferenças para revisar.
