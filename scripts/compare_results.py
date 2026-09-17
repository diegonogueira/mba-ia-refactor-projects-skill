#!/usr/bin/env python3
"""Compara duas execuções do smoke_test.py (baseline x refatorado).

Uso:
    python3 scripts/compare_results.py <baseline.json> <refatorado.json>

Para cada requisição (mesma ordem nos dois arquivos) compara o status HTTP e o
"shape" da resposta (chaves JSON até 2 níveis; `-campo` = removido, `+campo` = novo).
Imprime uma tabela Markdown e um resumo. Diferenças não são necessariamente regressões: mudanças de contrato
intencionais (ex.: remoção de campos sensíveis) devem ser justificadas.
"""
import json
import sys


def shape_diff(old, new, path=""):
    """Lista as diferenças estruturais entre dois shapes (chaves removidas/novas, listas que ficaram vazias...)."""
    label = path or "(raiz)"
    if isinstance(old, dict) and isinstance(new, dict):
        diffs = [f"-{path + '.' if path else ''}{k}" for k in sorted(set(old) - set(new))]
        diffs += [f"+{path + '.' if path else ''}{k}" for k in sorted(set(new) - set(old))]
        for k in sorted(set(old) & set(new)):
            diffs += shape_diff(old[k], new[k], f"{path + '.' if path else ''}{k}")
        return diffs
    if isinstance(old, list) and isinstance(new, list):
        if old and not new:
            return [f"{label}: lista vazia"]
        if new and not old:
            return [f"{label}: lista passou a ter itens"]
        if old and new:
            return shape_diff(old[0], new[0], f"{path}[]")
        return []
    if old != new:
        return [f"{label}: {old} → {new}"]
    return []


def main():
    base = json.load(open(sys.argv[1], encoding="utf-8"))
    new = json.load(open(sys.argv[2], encoding="utf-8"))
    if len(base) != len(new):
        print(f"AVISO: quantidade de checks diferente ({len(base)} x {len(new)})")

    same = 0
    rows = []
    for b, n in zip(base, new):
        status_ok = b["status"] == n["status"]
        shape_ok = b.get("shape") == n.get("shape") if b.get("json") and n.get("json") else b.get("json") == n.get("json")
        if status_ok and shape_ok:
            same += 1
            verdict = "igual"
        else:
            parts = []
            if not status_ok:
                parts.append(f"status {b['status']} → {n['status']}")
            if not shape_ok:
                detail = shape_diff(b.get("shape"), n.get("shape")) if b.get("json") and n.get("json") else ["texto ↔ JSON"]
                parts.append("shape (" + ", ".join(detail) + ")")
            verdict = "DIFERENTE: " + "; ".join(parts)
        rows.append(f"| {b['method']} | `{b['path']}` | {b['status']} | {n['status']} | {verdict} |")

    print("| Método | Rota | Original | Refatorado | Resultado |")
    print("|---|---|---|---|---|")
    print("\n".join(rows))
    print(f"\n{same}/{len(base)} checks idênticos (status + shape); {len(base) - same} diferenças para revisar.")


if __name__ == "__main__":
    main()
