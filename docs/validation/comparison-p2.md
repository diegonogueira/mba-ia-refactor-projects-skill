| # | Método | Rota | Original | Refatorado | Resultado |
|---|---|---|---|---|---|
| 1 | POST | `/api/checkout` | 200 | 200 | igual |
| 2 | POST | `/api/checkout` | 200 | 200 | igual |
| 3 | POST | `/api/checkout` | 400 | 400 | igual |
| 4 | POST | `/api/checkout` | 404 | 404 | igual |
| 5 | POST | `/api/checkout` | 400 | 400 | igual |
| 6 | GET | `/api/admin/financial-report` | 200 | 200 | igual |
| 7 | DELETE | `/api/users/1` | 200 | 200 | igual |
| 8 | GET | `/api/admin/financial-report` | 200 | 200 | DIFERENTE (esperado: relatório financeiro sem alunos órfãos/receita fantasma após DELETE /api/users/1 (exceção 5: integridade referencial)): shape ([].students: lista vazia) |

7/8 checks idênticos (status + shape); 1 diferenças esperadas (mudanças de contrato documentadas); 0 diferenças não esperadas.
