| Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|
| GET | `/` | 200 | 200 | igual |
| GET | `/health` | 200 | 200 | igual |
| GET | `/tasks` | 200 | 200 | igual |
| GET | `/tasks/1` | 200 | 200 | igual |
| GET | `/tasks/9999` | 404 | 404 | igual |
| POST | `/tasks` | 201 | 201 | igual |
| POST | `/tasks` | 400 | 400 | igual |
| POST | `/tasks` | 400 | 400 | igual |
| POST | `/tasks` | 400 | 400 | igual |
| POST | `/tasks` | 400 | 400 | igual |
| POST | `/tasks` | 404 | 404 | igual |
| POST | `/tasks` | 400 | 400 | igual |
| PUT | `/tasks/1` | 200 | 200 | igual |
| PUT | `/tasks/1` | 400 | 400 | igual |
| PUT | `/tasks/9999` | 404 | 404 | igual |
| DELETE | `/tasks/2` | 200 | 200 | igual |
| DELETE | `/tasks/9999` | 404 | 404 | igual |
| GET | `/tasks/search?q=API` | 200 | 200 | igual |
| GET | `/tasks/search?status=pending&priority=1` | 200 | 200 | igual |
| GET | `/tasks/stats` | 200 | 200 | igual |
| GET | `/users` | 200 | 200 | igual |
| GET | `/users/1` | 200 | 200 | DIFERENTE: shape (-password) |
| GET | `/users/9999` | 404 | 404 | igual |
| POST | `/users` | 201 | 201 | DIFERENTE: shape (-password) |
| POST | `/users` | 409 | 409 | igual |
| POST | `/users` | 400 | 400 | igual |
| POST | `/users` | 400 | 400 | igual |
| PUT | `/users/2` | 200 | 200 | DIFERENTE: shape (-password) |
| PUT | `/users/9999` | 404 | 404 | igual |
| GET | `/users/1/tasks` | 200 | 200 | igual |
| GET | `/users/9999/tasks` | 404 | 404 | igual |
| POST | `/login` | 200 | 200 | DIFERENTE: shape (-user.password) |
| POST | `/login` | 401 | 401 | igual |
| POST | `/login` | 400 | 400 | igual |
| GET | `/reports/summary` | 200 | 200 | igual |
| GET | `/reports/user/1` | 200 | 200 | igual |
| GET | `/reports/user/9999` | 404 | 404 | igual |
| GET | `/categories` | 200 | 200 | igual |
| POST | `/categories` | 201 | 201 | igual |
| POST | `/categories` | 400 | 400 | igual |
| PUT | `/categories/1` | 200 | 200 | igual |
| PUT | `/categories/9999` | 404 | 404 | igual |
| DELETE | `/categories/9999` | 404 | 404 | igual |
| DELETE | `/users/3` | 200 | 200 | igual |

40/44 checks idênticos (status + shape); 4 diferenças para revisar.
