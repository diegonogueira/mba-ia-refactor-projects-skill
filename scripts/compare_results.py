#!/usr/bin/env python3
"""Compara duas execuções do smoke_test.py (baseline x refatorado).

Uso:
    python3 scripts/compare_results.py <baseline.json> <refatorado.json> [--expected <arquivo.json> <projeto>]

Para cada requisição (mesma ordem nos dois arquivos) compara o status HTTP e o
"shape" da resposta (chaves JSON até 2 níveis; `-campo` = removido, `+campo` = novo).
Imprime uma tabela Markdown e um resumo.

Com `--expected`, cada diferença precisa estar declarada no arquivo de diferenças
esperadas (mudanças de contrato documentadas), indexada por "<n>" (posição do check,
a partir de 1). O valor pode ser:

    "<n>": "motivo"                              → só diferença de shape é aceita
    "<n>": {"status": "200->403", "motivo": "…"} → também aceita essa troca de status

Qualquer diferença não declarada — inclusive uma troca de status onde só se esperava
mudança de shape — é tratada como regressão e o script termina com código 1.
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
    args = sys.argv[1:]
    expected = {}
    gate = "--expected" in args
    if gate:
        i = args.index("--expected")
        expected = json.load(open(args[i + 1], encoding="utf-8")).get(args[i + 2], {})
        args = args[:i]
    base = json.load(open(args[0], encoding="utf-8"))
    new = json.load(open(args[1], encoding="utf-8"))
    if len(base) != len(new):
        print(f"AVISO: quantidade de checks diferente ({len(base)} x {len(new)})")

    same, documented, regressions = 0, 0, 0
    rows = []
    for index, (b, n) in enumerate(zip(base, new), start=1):
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
            entry = expected.get(str(index))
            reason, allowed_status = None, None
            if isinstance(entry, dict):
                reason, allowed_status = entry.get("motivo"), entry.get("status")
            elif entry:
                reason = entry
            status_declared = status_ok or (allowed_status == f"{b['status']}->{n['status']}")
            if reason and status_declared:
                documented += 1
                verdict = "DIFERENTE (esperado: " + reason + "): " + "; ".join(parts)
            else:
                regressions += 1
                missing = "" if reason else ""
                if reason and not status_declared:
                    missing = f" — troca de status {b['status']}->{n['status']} não declarada"
                verdict = "DIFERENTE" + (" — NÃO ESPERADO" + missing if gate else "") + ": " + "; ".join(parts)
        rows.append(f"| {index} | {b['method']} | `{b['path']}` | {b['status']} | {n['status']} | {verdict} |")

    print("| # | Método | Rota | Original | Refatorado | Resultado |")
    print("|---|---|---|---|---|---|")
    print("\n".join(rows))
    if gate:
        print(f"\n{same}/{len(base)} checks idênticos (status + shape); {documented} diferenças esperadas "
              f"(mudanças de contrato documentadas); {regressions} diferenças não esperadas.")
        sys.exit(1 if regressions or len(base) != len(new) else 0)
    print(f"\n{same}/{len(base)} checks idênticos (status + shape); {len(base) - same} diferenças para revisar.")


if __name__ == "__main__":
    main()
