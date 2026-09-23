#!/usr/bin/env bash
# Provas de fechamento de segurança — verificam, com a aplicação no ar, que os achados
# CRITICAL/HIGH de autorização realmente foram fechados (e não só declarados no relatório).
#
# Uso:  scripts/security_probes.sh [1|2|3|all]      (padrão: all)
#
# Cada prova imprime PASS/FAIL; o script termina com código != 0 se alguma falhar.
# Requisitos: python3 (>= 3.10), node (>= 20.17) + npm, curl. Usa `uv` se existir.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/refactor-arch-probes.XXXXXX")"
SERVER_PID=""
FAILED=0

cleanup() { [[ -n "$SERVER_PID" ]] && { kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null; }; }
trap 'cleanup; rm -rf "$WORK"' EXIT

copy_project() {
  mkdir -p "$2"
  (cd "$ROOT/$1" && tar --exclude=node_modules --exclude=.venv --exclude=.claude --exclude='*.db' --exclude=instance --exclude=__pycache__ -cf - .) | tar -xf - -C "$2"
}

python_env() {
  if command -v uv >/dev/null 2>&1; then
    uv venv -q "$1/.venv" && uv pip install -q --python "$1/.venv/bin/python" -r "$1/requirements.txt"
  else
    python3 -m venv "$1/.venv" && "$1/.venv/bin/pip" install -q -r "$1/requirements.txt"
  fi
}

start() { # <dir> <port> <log> <cmd...>   (variáveis de ambiente extras vêm do chamador)
  local dir=$1 port=$2 log=$3; shift 3
  (cd "$dir" && exec setsid "$@" >"$log" 2>&1 </dev/null) &
  SERVER_PID=$!
  for _ in $(seq 1 60); do curl -s -o /dev/null "http://127.0.0.1:$port/" && return 0; sleep 0.5; done
  echo "  ✗ servidor não subiu (veja $log)"; FAILED=1; return 1
}

stop() { cleanup; SERVER_PID=""; sleep 1; }

probe() { # <descrição> <status esperado> <curl args...>
  local what=$1 expected=$2; shift 2
  local got
  got=$(curl -s -o /dev/null -w '%{http_code}' "$@")
  if [[ "$got" == "$expected" ]]; then
    echo "  PASS  $what (HTTP $got)"
  else
    echo "  FAIL  $what — esperado $expected, obtido $got"; FAILED=1
  fi
}

probe_body() { # <descrição> <regex que NÃO pode aparecer no corpo> <curl args...>
  local what=$1 forbidden=$2; shift 2
  if curl -s "$@" | grep -qiE "$forbidden"; then
    echo "  FAIL  $what — resposta contém \"$forbidden\""; FAILED=1
  else
    echo "  PASS  $what"
  fi
}

estoque_produto() { curl -s "localhost:5000/produtos/$1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dados"]["estoque"])'; }

check() { # <descrição> <obtido> <esperado>
  if [[ "$2" == "$3" ]]; then echo "  PASS  $1 ($2)"; else echo "  FAIL  $1 — esperado $3, obtido $2"; FAILED=1; fi
}

# Impact do HIGH de AP-07 no audit-project-1.md: "cancelar devolve estoque" era anunciado e não implementado.
probe_estoque_cancelamento() {
  local inicial pedido
  inicial=$(estoque_produto 2)
  pedido=$(curl -s -X POST localhost:5000/pedidos -H 'Content-Type: application/json' \
    -d '{"usuario_id":1,"itens":[{"produto_id":2,"quantidade":3}]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["dados"]["pedido_id"])')
  check "pedido baixa o estoque" "$(estoque_produto 2)" "$((inicial - 3))"
  probe "cancelamento responde como antes" 200 -X PUT "localhost:5000/pedidos/$pedido/status" -H 'Content-Type: application/json' -d '{"status":"cancelado"}'
  check "cancelar devolve o estoque" "$(estoque_produto 2)" "$inicial"
  curl -s -o /dev/null -X PUT "localhost:5000/pedidos/$pedido/status" -H 'Content-Type: application/json' -d '{"status":"cancelado"}'
  check "cancelar de novo não devolve em dobro" "$(estoque_produto 2)" "$inicial"
  probe "reabrir pedido cancelado é recusado" 400 -X PUT "localhost:5000/pedidos/$pedido/status" -H 'Content-Type: application/json' -d '{"status":"aprovado"}'
  check "reabrir pedido cancelado não mexe no estoque" "$(estoque_produto 2)" "$inicial"
}

probes_1() {
  echo "=== Projeto 1: code-smells-project ==="
  local d="$WORK/p1"; copy_project code-smells-project "$d"; python_env "$d" || return 1
  SEED_PASSWORD=senha-de-teste-123 start "$d" 5000 "$WORK/p1.log" env SEED_PASSWORD=senha-de-teste-123 "$d/.venv/bin/python" app.py || return 1
  probe "endpoint de SQL arbitrário fechado por padrão" 403 -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -d '{"sql":"SELECT 1"}'
  probe "reset do banco fechado por padrão" 403 -X POST localhost:5000/admin/reset-db
  probe "405 continua respondendo" 405 -X DELETE localhost:5000/health
  if curl -s -D- -o /dev/null -X DELETE localhost:5000/health | grep -qi '^allow:'; then
    echo "  PASS  405 preserva o header Allow"; else echo "  FAIL  405 sem header Allow"; FAILED=1; fi
  probe "listagem de usuários fechada para anônimo" 403 localhost:5000/usuarios
  probe "relatório de vendas fechado para anônimo" 403 localhost:5000/relatorios/vendas
  probe_body "listagem de usuários não expõe senha" '"senha"' localhost:5000/usuarios
  probe_body "health não expõe segredos" 'secret_key|db_path' localhost:5000/health
  probe "login com a senha do seed configurada" 200 -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"admin@loja.com","senha":"senha-de-teste-123"}'
  probe "injeção de SQL no login não autentica" 401 -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"admin@loja.com'"'"' --","senha":"x"}'
  if curl -s -D- -o /dev/null -H 'Origin: http://origem-desconhecida.example' localhost:5000/produtos | grep -qi 'access-control-allow-origin'; then
    echo "  FAIL  CORS reflete origem desconhecida"; FAILED=1
  else
    echo "  PASS  CORS não reflete origem desconhecida"
  fi
  probe_estoque_cancelamento
  stop
  echo "  -- com os endpoints administrativos habilitados --"
  start "$d" 5000 "$WORK/p1-admin.log" env ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=token-de-teste SEED_PASSWORD=senha-de-teste-123 "$d/.venv/bin/python" app.py || return 1
  probe "consulta administrativa com token" 200 -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -H 'X-Admin-Token: token-de-teste' -d '{"sql":"SELECT id FROM produtos"}'
  probe "consulta que cita coluna de credencial é recusada" 400 -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -H 'X-Admin-Token: token-de-teste' -d '{"sql":"SELECT email, senha FROM usuarios"}'
  probe_body "SELECT * em usuarios não devolve hash" 'scrypt|pbkdf2' -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -H 'X-Admin-Token: token-de-teste' -d '{"sql":"SELECT * FROM usuarios"}'
  probe_body "consulta composta que renomeia colunas não devolve hash" 'scrypt|pbkdf2' -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -H 'X-Admin-Token: token-de-teste' -d '{"sql":"SELECT * FROM (VALUES (0,0,0,0,0,0) UNION ALL SELECT * FROM usuarios)"}'
  probe "token errado é rejeitado" 403 -X POST localhost:5000/admin/query -H 'Content-Type: application/json' -H 'X-Admin-Token: errado' -d '{"sql":"SELECT 1"}'
  stop
}

probes_2() {
  echo "=== Projeto 2: ecommerce-api-legacy ==="
  local d="$WORK/p2"; copy_project ecommerce-api-legacy "$d"
  (cd "$d" && npm ci --no-audit --no-fund >/dev/null 2>&1) || { echo "  ✗ npm ci falhou"; FAILED=1; return 1; }
  start "$d" 3000 "$WORK/p2.log" node src/app.js || return 1
  probe "relatório financeiro fechado por padrão" 403 localhost:3000/api/admin/financial-report
  probe "exclusão de usuário fechada por padrão" 403 -X DELETE localhost:3000/api/users/1
  probe "checkout continua público" 200 -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' -d '{"usr":"Ana","eml":"ana.probe@teste.com","pwd":"segredo123","c_id":2,"card":"4111222233334444"}'
  probe "checkout duplicado é recusado" 400 -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' -d '{"usr":"Ana","eml":"ana.probe@teste.com","pwd":"segredo123","c_id":2,"card":"4111222233334444"}'
  if grep -qE '4111222233334444|pk_live' "$WORK/p2.log"; then echo "  FAIL  log expõe cartão/chave"; FAILED=1; else echo "  PASS  log não expõe cartão nem chave do gateway"; fi
  stop
  echo "  -- com as rotas administrativas habilitadas --"
  start "$d" 3000 "$WORK/p2-admin.log" env ADMIN_ENDPOINTS_ENABLED=true ADMIN_TOKEN=token-de-teste node src/app.js || return 1
  probe "relatório financeiro com token" 200 -H 'X-Admin-Token: token-de-teste' localhost:3000/api/admin/financial-report
  probe "relatório financeiro sem token" 403 localhost:3000/api/admin/financial-report
  stop
}

probes_3() {
  echo "=== Projeto 3: task-manager-api ==="
  local d="$WORK/p3"; copy_project task-manager-api "$d"; python_env "$d" || return 1
  (cd "$d" && .venv/bin/python seed.py >/dev/null 2>&1)
  start "$d" 5000 "$WORK/p3.log" "$d/.venv/bin/python" app.py || return 1
  probe "auto-cadastro como admin é recusado" 403 -X POST localhost:5000/users -H 'Content-Type: application/json' -d '{"name":"Probe","email":"probe.admin@teste.com","password":"segredo123","role":"admin"}'
  probe "auto-cadastro como manager é recusado" 403 -X POST localhost:5000/users -H 'Content-Type: application/json' -d '{"name":"Probe","email":"probe.manager@teste.com","password":"segredo123","role":"manager"}'
  probe "auto-cadastro comum continua funcionando" 201 -X POST localhost:5000/users -H 'Content-Type: application/json' -d '{"name":"Probe","email":"probe.user@teste.com","password":"segredo123","role":"user"}'
  probe "promoção de conta alheia é recusada" 403 -X PUT localhost:5000/users/2 -H 'Content-Type: application/json' -d '{"role":"admin"}'
  probe "desativar conta alheia é recusado" 403 -X PUT localhost:5000/users/2 -H 'Content-Type: application/json' -d '{"active":false}'
  probe "atualização legítima continua funcionando" 200 -X PUT localhost:5000/users/2 -H 'Content-Type: application/json' -d '{"name":"Maria S."}'
  probe_body "resposta de usuário não traz hash de senha" '"password"' localhost:5000/users/1
  if curl -s -D- -o /dev/null -H 'Origin: http://origem-desconhecida.example' localhost:5000/tasks | grep -qi 'access-control-allow-origin'; then
    echo "  FAIL  CORS reflete origem desconhecida"; FAILED=1
  else
    echo "  PASS  CORS não reflete origem desconhecida"
  fi
  stop
  # Falha de escrita real: o e-mail duplicado é barrado pelo validador antes do banco, então força-se um
  # IntegrityError de verdade para ver o que o logger grava.
  ( cd "$d" && .venv/bin/python - <<'PY' > "$WORK/p3-integrity.log" 2>&1
import logging
logging.basicConfig(level=logging.DEBUG)
from src.app import create_app
from src.models.database import commit, db
from src.models.user_model import User
app = create_app()
with app.app_context():
    existente = db.session.execute(db.select(User)).scalars().first()
    duplicado = User(name="Dup", email=existente.email, role="user")
    duplicado.set_password("segredo123")
    db.session.add(duplicado)
    try:
        commit("Erro ao criar usuário")
    except Exception as exc:
        print("erro tratado:", type(exc).__name__)
PY
  )
  if grep -qiE 'scrypt|pbkdf2|parameters: \(|INSERT INTO users' "$WORK/p3-integrity.log"; then
    echo "  FAIL  log de erro expõe parâmetros/hash de senha"; FAILED=1
  else
    echo "  PASS  log de erro não expõe parâmetros do banco (IntegrityError forçado)"
  fi
}

case "${1:-all}" in
  1) probes_1 ;;
  2) probes_2 ;;
  3) probes_3 ;;
  all) probes_1; probes_2; probes_3 ;;
  *) echo "uso: $0 [1|2|3|all]"; exit 2 ;;
esac

echo
[[ $FAILED -eq 0 ]] && echo "✓ Todas as provas de segurança passaram" || echo "✗ Alguma prova falhou"
exit $FAILED
