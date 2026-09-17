| Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|
| POST | `/api/checkout` | 200 | 200 | igual |
| POST | `/api/checkout` | 200 | 200 | igual |
| POST | `/api/checkout` | 400 | 400 | igual |
| POST | `/api/checkout` | 404 | 404 | igual |
| POST | `/api/checkout` | 400 | 400 | igual |
| GET | `/api/admin/financial-report` | 200 | 200 | igual |
| DELETE | `/api/users/1` | 200 | 200 | igual |
| GET | `/api/admin/financial-report` | 200 | 200 | DIFERENTE: shape ([].students: lista vazia) |

7/8 checks idênticos (status + shape); 1 diferenças para revisar.
