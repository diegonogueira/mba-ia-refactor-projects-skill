#!/usr/bin/env python3
"""Evaluator harness: hits every endpoint of a project and records status + response shape.

usage: smoke.py <p1|p2|p3> <base_url> <out.json>
"""
import json
import sys
import time
import urllib.error
import urllib.request

UNIQ = str(int(time.time() * 1000))[-8:]

P1 = [
    ("GET", "/", None),
    ("GET", "/health", None),
    ("GET", "/produtos", None),
    ("GET", "/produtos/busca?q=Mouse", None),
    ("GET", "/produtos/busca?categoria=informatica&preco_min=50&preco_max=300", None),
    ("GET", "/produtos/busca?q=%27%20OR%20%271%27%3D%271", None),
    ("GET", "/produtos/1", None),
    ("GET", "/produtos/9999", None),
    ("POST", "/produtos", {"nome": "Produto Teste", "descricao": "desc", "preco": 10.5, "estoque": 5, "categoria": "livros"}),
    ("POST", "/produtos", {}),
    ("POST", "/produtos", {"nome": "X"}),
    ("POST", "/produtos", {"nome": "Produto", "preco": 1, "estoque": 1, "categoria": "invalida"}),
    ("POST", "/produtos", {"nome": "Produto", "preco": -1, "estoque": 1}),
    ("PUT", "/produtos/2", {"nome": "Mouse Wireless Pro", "descricao": "Mouse", "preco": 99.9, "estoque": 50, "categoria": "informatica"}),
    ("PUT", "/produtos/9999", {"nome": "Nada", "preco": 1, "estoque": 1}),
    ("DELETE", "/produtos/11", None),
    ("DELETE", "/produtos/9999", None),
    ("GET", "/usuarios", None),
    ("GET", "/usuarios/1", None),
    ("GET", "/usuarios/9999", None),
    ("POST", "/usuarios", {"nome": "Novo", "email": f"novo{UNIQ}@email.com", "senha": "segredo123"}),
    ("POST", "/usuarios", {"nome": "Novo"}),
    ("POST", "/login", {"email": "admin@loja.com", "senha": "admin123"}),
    ("POST", "/login", {"email": "admin@loja.com", "senha": "errada"}),
    ("POST", "/login", {"email": "", "senha": ""}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 1}, {"produto_id": 3, "quantidade": 2}]}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 99999}]}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 9999, "quantidade": 1}]}),
    ("POST", "/pedidos", {"usuario_id": 2, "itens": []}),
    ("GET", "/pedidos", None),
    ("GET", "/pedidos/usuario/2", None),
    ("PUT", "/pedidos/1/status", {"status": "aprovado"}),
    ("PUT", "/pedidos/1/status", {"status": "invalido"}),
    ("GET", "/relatorios/vendas", None),
    ("POST", "/admin/query", {"sql": "SELECT COUNT(*) AS n FROM usuarios"}),
    ("POST", "/admin/reset-db", None),
]

P2 = [
    ("POST", "/api/checkout", {"usr": "Guilherme", "eml": f"gui{UNIQ}@fullcycle.com.br", "pwd": "senhaforte", "c_id": 2, "card": "4111222233334444"}),
    ("POST", "/api/checkout", {"usr": "Leonan", "eml": "leonan@fullcycle.com.br", "pwd": "123", "c_id": 2, "card": "4111222233334444"}),
    ("POST", "/api/checkout", {"usr": "João", "eml": "joao@teste.com", "pwd": "123", "c_id": 1, "card": "5111222233334444"}),
    ("POST", "/api/checkout", {"usr": "João", "eml": "joao@teste.com", "c_id": 999, "card": "4111222233334444"}),
    ("POST", "/api/checkout", {"usr": "João"}),
    ("GET", "/api/admin/financial-report", None),
    ("DELETE", "/api/users/1", None),
    ("GET", "/api/admin/financial-report", None),
]

P3 = [
    ("GET", "/", None),
    ("GET", "/health", None),
    ("GET", "/tasks", None),
    ("GET", "/tasks/1", None),
    ("GET", "/tasks/9999", None),
    ("POST", "/tasks", {"title": "Nova task", "description": "d", "priority": 2, "user_id": 1, "category_id": 1, "due_date": "2030-01-01", "tags": ["a", "b"]}),
    ("POST", "/tasks", {"title": "ab"}),
    ("POST", "/tasks", {}),
    ("POST", "/tasks", {"title": "Task status", "status": "xpto"}),
    ("POST", "/tasks", {"title": "Task prio", "priority": 9}),
    ("POST", "/tasks", {"title": "Task user", "user_id": 9999}),
    ("POST", "/tasks", {"title": "Task date", "due_date": "01-01-2030"}),
    ("PUT", "/tasks/1", {"status": "in_progress", "priority": 2}),
    ("PUT", "/tasks/1", {"status": "xpto"}),
    ("PUT", "/tasks/9999", {"status": "done"}),
    ("DELETE", "/tasks/2", None),
    ("DELETE", "/tasks/9999", None),
    ("GET", "/tasks/search?q=API", None),
    ("GET", "/tasks/search?status=pending&priority=1", None),
    ("GET", "/tasks/stats", None),
    ("GET", "/users", None),
    ("GET", "/users/1", None),
    ("GET", "/users/9999", None),
    ("POST", "/users", {"name": "Ana", "email": f"ana{UNIQ}@email.com", "password": "segredo", "role": "user"}),
    ("POST", "/users", {"name": "Ana", "email": "joao@email.com", "password": "segredo"}),
    ("POST", "/users", {"name": "Ana", "email": "invalido", "password": "segredo"}),
    ("POST", "/users", {"name": "Ana"}),
    ("PUT", "/users/2", {"name": "Maria S."}),
    ("PUT", "/users/9999", {"name": "x"}),
    ("GET", "/users/1/tasks", None),
    ("GET", "/users/9999/tasks", None),
    ("POST", "/login", {"email": "joao@email.com", "password": "1234"}),
    ("POST", "/login", {"email": "joao@email.com", "password": "errada"}),
    ("POST", "/login", {}),
    ("GET", "/reports/summary", None),
    ("GET", "/reports/user/1", None),
    ("GET", "/reports/user/9999", None),
    ("GET", "/categories", None),
    ("POST", "/categories", {"name": "QA", "description": "Testes", "color": "#123456"}),
    ("POST", "/categories", {}),
    ("PUT", "/categories/1", {"description": "Backend tasks"}),
    ("PUT", "/categories/9999", {"name": "x"}),
    ("DELETE", "/categories/9999", None),
    ("DELETE", "/users/3", None),
]


def shape(value, depth=0):
    if isinstance(value, dict):
        if depth >= 2:
            return "object"
        return {k: shape(v, depth + 1) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def call(base, method, path, body):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status, raw, ctype = resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        status, raw, ctype = err.code, err.read(), err.headers.get("Content-Type", "")
    except Exception as err:  # connection refused, timeout...
        return {"status": "ERR", "error": str(err)}
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)
        return {"status": status, "json": True, "shape": shape(parsed), "body": text[:400]}
    except ValueError:
        return {"status": status, "json": False, "body": text[:200], "ctype": ctype}


def main():
    project, base, out = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
    plan = {"p1": P1, "p2": P2, "p3": P3}[project]
    results = []
    for method, path, body in plan:
        res = call(base, method, path, body)
        res.update({"method": method, "path": path})
        results.append(res)
        print(f"{method:6} {path:70} -> {res['status']}")
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
