#!/usr/bin/env python3
"""Confere as localizações citadas nas linhas `- **File:**` de um relatório de auditoria.

Cada `caminho:linha` ou `caminho:inicio-fim` precisa existir no código ORIGINAL do projeto
(o que foi auditado) e estar dentro do número de linhas do arquivo. Com --show, imprime
a primeira linha citada de cada localização, para conferência manual do conteúdo.

Uso:
    git worktree add /tmp/original 6d1ce62
    python3 scripts/check_report_locations.py reports/audit-project-1.md /tmp/original/code-smells-project [--show]
"""
import re
import sys
from pathlib import Path

report, root = Path(sys.argv[1]), Path(sys.argv[2])
show = "--show" in sys.argv
bad = 0
total = 0
current = None
for line in report.read_text(encoding="utf-8").splitlines():
    if line.startswith("### ["):
        current = line
    m = re.match(r"- \*\*File:\*\* (.*)", line)
    if not m:
        continue
    for path, start, end in re.findall(r"`([\w./-]+):(\d+)(?:-(\d+))?`", m.group(1)):
        total += 1
        f = root / path
        if not f.exists():
            print("ARQUIVO INEXISTENTE", path, "em", current)
            bad += 1
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        s, e = int(start), int(end or start)
        if not (1 <= s <= e <= len(lines)):
            print(f"FORA DO INTERVALO {path}:{s}-{e} (o arquivo tem {len(lines)} linhas) em {current}")
            bad += 1
        elif show:
            print(f"{current}\n   {path}:{s}: {lines[s-1].strip()[:110]}")
print(f"{total} localizações conferidas, {bad} problemas")
sys.exit(1 if bad else 0)
