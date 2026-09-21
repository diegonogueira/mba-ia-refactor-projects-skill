| # | Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|---|
| 1 | POST | `/api/checkout` | 200 | 200 | igual |
| 2 | POST | `/api/checkout` | 200 | 200 | igual |
| 3 | POST | `/api/checkout` | 400 | 400 | igual |
| 4 | POST | `/api/checkout` | 404 | 404 | igual |
| 5 | POST | `/api/checkout` | 400 | 400 | igual |
| 6 | GET | `/api/admin/financial-report` | 200 | 403 | DIFERENTE (esperado: GET /api/admin/financial-report — rota destrutiva/administrativa fechada por padrão (exceção 2); com ADMIN_ENDPOINTS_ENABLED=true + ADMIN_TOKEN volta a responder como o original): status 200 → 403; shape (texto ↔ JSON) |
| 7 | DELETE | `/api/users/1` | 200 | 403 | DIFERENTE (esperado: DELETE /api/users/:id — rota destrutiva fechada por padrão (exceção 2); com ADMIN_ENDPOINTS_ENABLED=true + ADMIN_TOKEN volta a responder 200, agora apagando também matrículas e pagamentos do usuário e com a mensagem ajustada (exceção 5: integridade)): status 200 → 403 |
| 8 | GET | `/api/admin/financial-report` | 200 | 403 | DIFERENTE (esperado: GET /api/admin/financial-report — rota destrutiva/administrativa fechada por padrão (exceção 2); com ADMIN_ENDPOINTS_ENABLED=true + ADMIN_TOKEN volta a responder como o original): status 200 → 403; shape (texto ↔ JSON) |

5/8 checks idênticos (status + shape); 3 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
