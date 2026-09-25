# Validation Guide (Phase 3)

Validation proves the refactoring kept the application working. It has two runs of the **same** smoke test: one against the original code (baseline, step 3.1) and one against the refactored code (step 3.4).

## Table of contents
1. Workspace and runtime setup
2. Booting the application
3. Writing the smoke test
4. Comparing with the baseline
5. Re-audit checks
6. Cleanup
7. Troubleshooting

---

## 1. Workspace and runtime setup

Keep validation artifacts **outside the project** so they are never committed:

```bash
VALIDATION_DIR="${TMPDIR:-/tmp}/refactor-arch/$(basename "$PWD")"
mkdir -p "$VALIDATION_DIR"
```

| Stack | Setup |
|---|---|
| Python | `python3 -m venv .venv` (already git-ignored in most repos; otherwise create it inside `$VALIDATION_DIR`) → `.venv/bin/pip install -r requirements.txt`. If `uv` is available: `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`. |
| Node.js | `npm ci` when a lockfile exists, else `npm install`. If a native module fails to load, see Troubleshooting. |
| Others | Use the project's documented build tool (`go build`, `mvn -q package`, `bundle install`). |

Record the runtime versions used (`python --version`, `node --version`) for the Phase 3 summary.

If a pinned dependency does not install on the available runtime, pick the nearest compatible version, note it, and use the **same** environment for baseline and refactored runs.

## 2. Booting the application

1. Run the documented setup steps first (e.g. seed script) — for both runs.
2. Start the server **in the background, in its own process group**, logging to a file:
   ```bash
   setsid <start command> > "$VALIDATION_DIR/server-<baseline|refactored>.log" 2>&1 < /dev/null &
   echo $! > "$VALIDATION_DIR/server.pid"
   ```
3. Wait until the port answers (max ~15 s):
   ```bash
   for i in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:<port>/" && break; sleep 0.5; done
   ```
   Any HTTP status (even 404) means it booted.
4. "Boots without errors" = the port answers **and** the log has no traceback / unhandled error.
5. Stop it after the smoke test: `kill -- -"$(cat "$VALIDATION_DIR/server.pid")"` (kills the whole group, including reloader children).

Use a fresh database state for each run when the app uses a file database: remove only the database file that the app itself creates (and that is git-ignored/untracked), then rerun the setup/seed step. For in-memory databases nothing is needed.

## 3. Writing the smoke test

Write one script in `$VALIDATION_DIR` (`smoke_test.sh` with curl, or `smoke_test.py` with `urllib`) that is reused unchanged for both runs.

Coverage rules:
- **Every endpoint from the Phase 1 inventory at least once** (method + path).
- Happy path with realistic payloads (take them from `api.http`, README, seed data, or the handler code).
- For each resource: one not-found (`/resource/999999`) and one invalid payload case, when the original handles them.
- Order requests so that dependent data exists (create before update/delete) and **destructive endpoints run last** (e.g. database reset, delete user).
- When the refactoring adds authentication to management routes (mvc-guidelines §9 exception 11), the smoke test logs in as the seeded admin first and sends `Authorization: Bearer <token>` to those routes in **both** runs (the original ignores the header), so the comparison stays like for like; 401/403 are checked by separate probes.
- Include one security probe per CRITICAL fix when applicable (e.g. SQL injection payload `' OR '1'='1` in a search/login field; request to a disabled admin endpoint).

For each request record: method, path, HTTP status, content type, and the response **shape** (JSON keys at the first two levels, or the text body for plain-text responses).

Minimal Python harness (standard library only):
```python
import json, sys, urllib.request, urllib.error

BASE = sys.argv[1]
OUT = sys.argv[2]
CHECKS = [
    ("GET", "/resource", None),
    ("POST", "/resource", {"name": "Example"}),
    # ... one tuple per request, in execution order
]

def shape(value, depth=0):
    if isinstance(value, dict):
        return {k: (shape(v, depth + 1) if depth < 1 else type(v).__name__) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    return type(value).__name__

results = []
for method, path, body in CHECKS:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status, raw = resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read().decode()
    try:
        body_shape = shape(json.loads(raw))
    except ValueError:
        body_shape = raw[:120]
    results.append({"method": method, "path": path, "status": status, "shape": body_shape})
    print(f"{status}  {method:6} {path}")

json.dump(results, open(OUT, "w"), indent=2, ensure_ascii=False)
```
Run: `python3 smoke_test.py http://127.0.0.1:<port> "$VALIDATION_DIR/<baseline|refactored>.json"`.

## 4. Comparing with the baseline

For each check (same index in both result files):

| Result | Meaning | Action |
|---|---|---|
| Same status and same shape | ✓ preserved | none |
| Different status or shape, explained by a documented contract exception (mvc-guidelines §9) | ✓ expected change | list under "Contract Changes" |
| Baseline 500 → refactored 400 for invalid input | ✓ improvement | list under "Contract Changes" |
| Any other difference (404 for an existing route, missing keys, 500) | ✗ regression | fix and rerun until none remain |
| Connection refused | ✗ boot failure | read the server log, fix, rerun |

Also compare a few **values** for read endpoints backed by seed data (e.g. list sizes, a known record's name) to catch wrong queries that keep the shape.

Summarize as `<matching>/<total> checks match the baseline (<n> documented contract changes)`.

## 5. Re-audit checks

On the refactored tree, rerun the catalog detection signals. Minimum commands (adapt extensions):

```bash
# secrets and debug flags
grep -rnEi "(secret|password|passwd|api[_-]?key|token)\w*['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]" --include=*.py --include=*.js src/ app.py 2>/dev/null
grep -rnE "debug\s*=\s*True|DEBUG['\"]?\]?\s*=\s*True" --include=*.py . --exclude-dir=.venv
# SQL built with concatenation/interpolation
grep -rnE "execute\(\s*f['\"]|execute\([^)]*['\"]\s*\+|(run|get|all)\(\s*\`[^\`]*\\$\{" --include=*.py --include=*.js src/
# data access leaking into controllers/views
grep -rnE "execute\(|db\.session|\.query\.|db\.(run|get|all)\(" src/controllers src/views
# deprecated APIs
grep -rnE "utcnow\(|\.query\.get\(|new Buffer\(|url\.parse\(" --include=*.py --include=*.js src/
```
Every hit must be either fixed or justified (e.g. parameterized constant fragments). Also confirm: old God modules deleted, no unused imports left in touched files, `.env.example` present.

## 6. Cleanup

- Stop every server process group you started (`ps` to double-check nothing listens on the port).
- Delete runtime artifacts created inside the project that are untracked: database files, logs, `__pycache__/` (use `git status --porcelain --ignored` to list them when git is available).
- Keep virtualenvs/`node_modules` only if they are git-ignored; never delete files that were versioned before the refactor unless they were migrated.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not locate the bindings file` / `invalid ELF header` (Node native module such as sqlite3, bcrypt) | Install scripts blocked by recent npm `allowScripts` policy, or binary built for another Node version | `npm install-scripts approve <pkg>` (adds `allowScripts` to `package.json`) then `npm rebuild <pkg>`; otherwise `npm rebuild <pkg> --build-from-source` |
| `ModuleNotFoundError: No module named 'src'` | Running from the wrong directory or missing `__init__.py` | Run from the project root; add `src/__init__.py` |
| Circular import on boot | Models importing the app or controllers importing each other at module level | Move wiring into `create_app()`; import inside functions only as last resort |
| `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` | Shared global connection | Per-request connection via `flask.g` (T-18) |
| `SQLITE_BUSY` / interleaved statements in Node | Concurrent transactions on one connection | Serialize transactions (queue/mutex) or use `db.serialize()` |
| `OSError: [Errno 98] Address already in use` | Previous server still running | Kill the old process group; verify with `ss -ltnp` or `lsof -i :<port>` |
| Flask server survives `kill <pid>` | Debug reloader child process | Kill the process group (`kill -- -<pgid>`) or run with debug disabled |
| `LegacyAPIWarning` / `DeprecationWarning` in logs after refactor | Deprecated call left behind | Grep and replace (T-14); run once with `python -W error::DeprecationWarning` to find them |
| Login fails after password hashing change | Seed/existing rows still hold old format | Re-seed with the new hash or implement verify-and-upgrade (T-04) |
| Endpoint shape differs only in key order | JSON serializers sort keys differently | Not a regression — compare parsed objects, not raw text |
