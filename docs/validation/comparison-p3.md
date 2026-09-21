| # | Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|---|
| 1 | GET | `/` | 200 | 200 | igual |
| 2 | GET | `/health` | 200 | 200 | igual |
| 3 | GET | `/tasks` | 200 | 200 | igual |
| 4 | GET | `/tasks/1` | 200 | 200 | igual |
| 5 | GET | `/tasks/9999` | 404 | 404 | igual |
| 6 | POST | `/tasks` | 201 | 201 | igual |
| 7 | POST | `/tasks` | 400 | 400 | igual |
| 8 | POST | `/tasks` | 400 | 400 | igual |
| 9 | POST | `/tasks` | 400 | 400 | igual |
| 10 | POST | `/tasks` | 400 | 400 | igual |
| 11 | POST | `/tasks` | 404 | 404 | igual |
| 12 | POST | `/tasks` | 400 | 400 | igual |
| 13 | PUT | `/tasks/1` | 200 | 200 | igual |
| 14 | PUT | `/tasks/1` | 400 | 400 | igual |
| 15 | PUT | `/tasks/9999` | 404 | 404 | igual |
| 16 | DELETE | `/tasks/2` | 200 | 200 | igual |
| 17 | DELETE | `/tasks/9999` | 404 | 404 | igual |
| 18 | GET | `/tasks/search?q=API` | 200 | 200 | igual |
| 19 | GET | `/tasks/search?status=pending&priority=1` | 200 | 200 | igual |
| 20 | GET | `/tasks/stats` | 200 | 200 | igual |
| 21 | GET | `/users` | 200 | 200 | igual |
| 22 | GET | `/users/1` | 200 | 200 | DIFERENTE (esperado: GET /users/<id> sem o hash de senha (exceção 1)): shape (-password) |
| 23 | GET | `/users/9999` | 404 | 404 | igual |
| 24 | POST | `/users` | 201 | 201 | DIFERENTE (esperado: POST /users sem o hash de senha na resposta (exceção 1)): shape (-password) |
| 25 | POST | `/users` | 409 | 409 | igual |
| 26 | POST | `/users` | 400 | 400 | igual |
| 27 | POST | `/users` | 400 | 400 | igual |
| 28 | PUT | `/users/2` | 200 | 200 | DIFERENTE (esperado: PUT /users/<id> sem o hash de senha na resposta (exceção 1)): shape (-password) |
| 29 | PUT | `/users/9999` | 404 | 404 | igual |
| 30 | GET | `/users/1/tasks` | 200 | 200 | igual |
| 31 | GET | `/users/9999/tasks` | 404 | 404 | igual |
| 32 | POST | `/login` | 200 | 401 | DIFERENTE (esperado: o seed deixou de ter senha no código (exceção 8): use SEED_PASSWORD=1234 no seed para reproduzir o login de demonstração, ou a senha sorteada que o seed imprime): status 200 → 401; shape (-message, -token, -user, +error) |
| 33 | POST | `/login` | 401 | 401 | igual |
| 34 | POST | `/login` | 400 | 400 | igual |
| 35 | GET | `/reports/summary` | 200 | 200 | igual |
| 36 | GET | `/reports/user/1` | 200 | 200 | igual |
| 37 | GET | `/reports/user/9999` | 404 | 404 | igual |
| 38 | GET | `/categories` | 200 | 200 | igual |
| 39 | POST | `/categories` | 201 | 201 | igual |
| 40 | POST | `/categories` | 400 | 400 | igual |
| 41 | PUT | `/categories/1` | 200 | 200 | igual |
| 42 | PUT | `/categories/9999` | 404 | 404 | igual |
| 43 | DELETE | `/categories/9999` | 404 | 404 | igual |
| 44 | DELETE | `/users/3` | 200 | 403 | DIFERENTE (esperado: DELETE /users/<id> — rota destrutiva/administrativa fechada por padrão (exceção 2); com ADMIN_ENDPOINTS_ENABLED=true + ADMIN_TOKEN volta a responder como o original): status 200 → 403; shape (-message, +error) |

39/44 checks idênticos (status + shape); 5 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
