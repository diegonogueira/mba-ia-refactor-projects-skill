#!/usr/bin/env bash
# Valida os projetos refatorados: instala dependências numa cópia temporária,
# sobe cada API, exercita todos os endpoints (scripts/smoke_test.py) e compara
# com a execução do código ORIGINAL (docs/validation/baseline-pN.json).
#
# Uso:  scripts/validate.sh [1|2|3|all]      (padrão: all)
# Requisitos: python3 (>= 3.10), node (>= 20.17) + npm, curl. Usa `uv` se existir.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/refactor-arch-validate.XXXXXX")"
OUT="$ROOT/docs/validation"
mkdir -p "$OUT"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

copy_project() { # <dir> <dest>
  mkdir -p "$2"
  (cd "$ROOT/$1" && tar --exclude=node_modules --exclude=.venv --exclude=.claude --exclude='*.db' --exclude=instance --exclude=__pycache__ -cf - .) | tar -xf - -C "$2"
}

python_env() { # <dest>
  if command -v uv >/dev/null 2>&1; then
    uv venv -q "$1/.venv" && uv pip install -q --python "$1/.venv/bin/python" -r "$1/requirements.txt"
  else
    python3 -m venv "$1/.venv" && "$1/.venv/bin/pip" install -q -r "$1/requirements.txt"
  fi
}

start_server() { # <dir> <port> <log> <cmd...>
  local dir=$1 port=$2 log=$3; shift 3
  if curl -s -o /dev/null "http://127.0.0.1:$port/"; then
    echo "ERRO: a porta $port já está em uso" >&2; exit 1
  fi
  if command -v setsid >/dev/null 2>&1; then
    (cd "$dir" && exec setsid "$@" >"$log" 2>&1 </dev/null) &
  else
    (cd "$dir" && exec "$@" >"$log" 2>&1 </dev/null) &
  fi
  SERVER_PID=$!
  for _ in $(seq 1 60); do
    curl -s -o /dev/null "http://127.0.0.1:$port/" && { echo "  ✓ servidor respondeu na porta $port"; return 0; }
    sleep 0.5
  done
  echo "  ✗ servidor não subiu; log:" >&2; cat "$log" >&2; exit 1
}

stop_server() {
  cleanup
  SERVER_PID=""
  sleep 1
}

sanitize_log() { # remove cores ANSI e IPs da rede local do log salvo
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
text = re.sub(r"\x1b\[[0-9;]*m", "", text)
text = re.sub(r"http://(10|172|192)\.\d+\.\d+\.\d+:", "http://<ip-da-rede-local>:", text)
open(path, "w", encoding="utf-8").write(text)
PY
}

run_checks() { # <n> <port>
  python3 "$ROOT/scripts/smoke_test.py" "p$1" "http://127.0.0.1:$2" "$OUT/refactored-p$1.json"
  echo
  python3 "$ROOT/scripts/compare_results.py" "$OUT/baseline-p$1.json" "$OUT/refactored-p$1.json" | tee "$OUT/comparison-p$1.md"
}

check_log() { # <n> — chamado depois de parar o servidor
  sanitize_log "$OUT/server-p$1.log"
  if grep -qiE "Traceback|UnhandledPromiseRejection|Error:" "$OUT/server-p$1.log"; then
    echo "  ✗ o log do servidor contém erros (veja docs/validation/server-p$1.log)"; exit 1
  fi
  echo "  ✓ log do servidor sem tracebacks (docs/validation/server-p$1.log)"
}

validate_1() {
  echo "=== Projeto 1: code-smells-project (Python/Flask) ==="
  local d="$WORK/p1"; copy_project code-smells-project "$d"; python_env "$d"
  start_server "$d" 5000 "$OUT/server-p1.log" "$d/.venv/bin/python" app.py
  run_checks 1 5000; stop_server; check_log 1
}

validate_2() {
  echo "=== Projeto 2: ecommerce-api-legacy (Node.js/Express) ==="
  local d="$WORK/p2"; copy_project ecommerce-api-legacy "$d"
  (cd "$d" && npm ci --no-audit --no-fund >/dev/null)
  start_server "$d" 3000 "$OUT/server-p2.log" node src/app.js
  run_checks 2 3000; stop_server; check_log 2
}

validate_3() {
  echo "=== Projeto 3: task-manager-api (Python/Flask) ==="
  local d="$WORK/p3"; copy_project task-manager-api "$d"; python_env "$d"
  (cd "$d" && .venv/bin/python seed.py)
  start_server "$d" 5000 "$OUT/server-p3.log" "$d/.venv/bin/python" app.py
  run_checks 3 5000; stop_server; check_log 3
}

case "${1:-all}" in
  1) validate_1 ;;
  2) validate_2 ;;
  3) validate_3 ;;
  all) validate_1; validate_2; validate_3 ;;
  *) echo "uso: $0 [1|2|3|all]"; exit 2 ;;
esac
rm -rf "$WORK"
echo "Resultados em docs/validation/"
