#!/usr/bin/env bash
# Valida os projetos refatorados: instala dependências numa cópia temporária,
# sobe cada API, exercita todos os endpoints (scripts/smoke_test.py) e compara
# com a execução do código ORIGINAL (docs/validation/baseline-pN.json).
#
# Uso:  scripts/validate.sh [1|2|3|all] [--save]
#   --save  grava resultados, comparações e logs em docs/validation/ (por padrão
#           ficam num diretório temporário e o repositório não é alterado)
#
# Termina com código != 0 se algum projeto não subir, se o log do servidor tiver
# traceback ou se surgir diferença em relação ao original que não esteja listada
# em docs/validation/expected-differences.json (mudanças de contrato documentadas).
#
# Requisitos: python3 (>= 3.10), node (>= 20.17) + npm, curl. Usa `uv` se existir.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="all"
SAVE=0
for arg in "$@"; do
  case "$arg" in
    1|2|3|all) TARGET="$arg" ;;
    --save) SAVE=1 ;;
    *) echo "uso: $0 [1|2|3|all] [--save]"; exit 2 ;;
  esac
done

WORK="$(mktemp -d "${TMPDIR:-/tmp}/refactor-arch-validate.XXXXXX")"
if [[ $SAVE -eq 1 ]]; then OUT="$ROOT/docs/validation"; else OUT="$WORK/results"; fi
mkdir -p "$OUT"
BASELINES="$ROOT/docs/validation"
EXPECTED="$ROOT/docs/validation/expected-differences.json"
SERVER_PID=""
FAILURES=()

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap 'cleanup; rm -rf "$WORK/p1" "$WORK/p2" "$WORK/p3"' EXIT

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
    echo "  ✗ a porta $port já está em uso"; return 1
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
  echo "  ✗ servidor não subiu; log:"; cat "$log"; return 1
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

check_project() { # <n> <port> — smoke test + comparação com o baseline + log
  local n=$1 port=$2 ok=0
  python3 "$ROOT/scripts/smoke_test.py" "p$n" "http://127.0.0.1:$port" "$OUT/refactored-p$n.json" >/dev/null || ok=1
  stop_server
  python3 "$ROOT/scripts/compare_results.py" "$BASELINES/baseline-p$n.json" "$OUT/refactored-p$n.json" \
    --expected "$EXPECTED" "p$n" > "$OUT/comparison-p$n.md" || ok=1
  tail -n 1 "$OUT/comparison-p$n.md" | sed 's/^/  /'
  grep "NÃO ESPERADO" "$OUT/comparison-p$n.md" | sed 's/^/  ✗ /' || true
  sanitize_log "$OUT/server-p$n.log"
  if grep -qiE "Traceback|UnhandledPromiseRejection|Error:" "$OUT/server-p$n.log"; then
    echo "  ✗ o log do servidor contém erros ($OUT/server-p$n.log)"; ok=1
  else
    echo "  ✓ log do servidor sem tracebacks"
  fi
  return $ok
}

validate_1() {
  echo "=== Projeto 1: code-smells-project (Python/Flask) ==="
  local d="$WORK/p1"; copy_project code-smells-project "$d"; python_env "$d" || return 1
  start_server "$d" 5000 "$OUT/server-p1.log" env SEED_PASSWORD=admin123 "$d/.venv/bin/python" app.py || { stop_server; return 1; }
  check_project 1 5000
}

validate_2() {
  echo "=== Projeto 2: ecommerce-api-legacy (Node.js/Express) ==="
  local d="$WORK/p2"; copy_project ecommerce-api-legacy "$d"
  (cd "$d" && npm ci --no-audit --no-fund >/dev/null 2>&1) || { echo "  ✗ npm ci falhou"; return 1; }
  start_server "$d" 3000 "$OUT/server-p2.log" node src/app.js || { stop_server; return 1; }
  check_project 2 3000
}

validate_3() {
  echo "=== Projeto 3: task-manager-api (Python/Flask) ==="
  local d="$WORK/p3"; copy_project task-manager-api "$d"; python_env "$d" || return 1
  (cd "$d" && .venv/bin/python seed.py 2>/dev/null | sed 's/^/  /') || return 1
  start_server "$d" 5000 "$OUT/server-p3.log" "$d/.venv/bin/python" app.py || { stop_server; return 1; }
  check_project 3 5000
}

run() { # <n>
  if ! "validate_$1"; then FAILURES+=("projeto $1"); fi
}

case "$TARGET" in
  all) run 1; run 2; run 3 ;;
  *) run "$TARGET" ;;
esac

echo
echo "Resultados: $OUT"
if [[ ${#FAILURES[@]} -gt 0 ]]; then
  echo "✗ Falhou: ${FAILURES[*]}"
  exit 1
fi
echo "✓ Todos os projetos validados"
