---
name: refactor-arch
description: Audits a backend codebase and refactors it to the MVC pattern in three gated phases - (1) detects language, framework, database, domain and current architecture; (2) cross-checks the code against an anti-pattern catalog (security, MVC/SOLID, performance, deprecated APIs) and prints a severity-ranked audit report with exact file and line, then asks for confirmation; (3) restructures the project into Models, Views/Routes and Controllers and validates that the app boots and every original endpoint still responds. Technology-agnostic (Python/Flask, Node.js/Express and other web backends). Use when the user runs /refactor-arch or asks to "audit the architecture", "find code smells", "refactor to MVC", "fix a legacy API" or "reorganize layers".
argument-hint: (no arguments - run from the project root)
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(find *)
  - Bash(ls *)
  - Bash(wc *)
  - Bash(grep *)
  - Bash(git status *)
  - Bash(npm audit *)
metadata:
  version: 1.2.0
  phases: analysis, audit, refactoring
---

# refactor-arch

Automated architecture audit and MVC refactoring for any web backend. You act as a senior software architect: first understand, then diagnose, then — only with human approval — transform and prove the result works.

## CRITICAL RULES (apply during the whole task)

1. **Phases run in strict order: 1 → 2 → (human confirmation) → 3.** Never skip or merge phases.
2. **Phases 1 and 2 are strictly READ-ONLY.** Do not create, edit, move or delete any file; do not install dependencies; do not start the application (booting can create database files). Only read, search and list.
3. **At the end of Phase 2, ask for confirmation and END YOUR TURN.** Continue to Phase 3 only if the user answers affirmatively (`y`, `yes`, `s`, `sim`, `proceed`). Any other answer: stop without touching files.
4. **Every finding must cite an exact `path:line` or `path:start-end`** taken from a real read of the file with line numbers (Read tool or `grep -n`). Never estimate line numbers. Never invent findings.
5. **Preserve the public contract** (routes, HTTP methods, request field names, success status codes, response field names, port and start command). The only allowed changes are the security/integrity exceptions listed in `references/mvc-guidelines.md` → "Contract preservation", and each one must be reported.
6. **Phase 3 is only complete when validation passes**: the app boots and every endpoint from the Phase 1 inventory responds like the baseline. If something cannot be fixed, say so explicitly — never report a check as passed without having run it.
7. **Stay inside the project.** The project is the directory where the skill was invoked. Do not list, read, search or modify anything outside it (no `..`, parent folders, sibling projects, other repositories). Exceptions: version-control metadata (`git status`, `git check-ignore`), the temporary validation directory described in `references/validation-guide.md`, and network access to package registries (dependency audit in Phase 2, installs in Phase 3).
8. **Write the free-text parts** (descriptions, impact, recommendations) in the language the user is using; if the invocation has no other text, use Brazilian Portuguese. Keep the fixed labels of the templates in English exactly as written.

## Reference files (load on demand, per phase)

| File | Knowledge | Load in |
|---|---|---|
| `references/project-analysis.md` | Heuristics to detect language, framework, database, domain, entry point, endpoints and current architecture | Phase 1 |
| `references/anti-patterns-catalog.md` | Anti-patterns with detection signals and severity rules (includes deprecated APIs) | Phase 2 and 3.5 |
| `references/report-template.md` | Exact output formats for Phase 1, the Phase 2 audit report and the Phase 3 summary | Phases 1, 2, 3 |
| `references/mvc-guidelines.md` | Target MVC architecture: layers, responsibilities, dependency rules, directory layouts per stack, contract preservation | Phase 3 |
| `references/refactoring-playbook.md` | Concrete transformations (before/after code) for each anti-pattern | Phase 3 |
| `references/validation-guide.md` | How to install, boot, smoke-test endpoints, compare with the baseline and troubleshoot | Phase 3 |

Paths are relative to this skill directory (`${CLAUDE_SKILL_DIR}`).

## Project snapshot (injected when the skill loads)

Files in the current directory (dependency, VCS and tool folders excluded):

```!
find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path './.claude/*' -not -name '*.pyc' 2>/dev/null | sort | head -300 || true
```

Uncommitted changes (empty = clean tree or not a git repository):

```!
git status --porcelain . 2>/dev/null | head -50 || true
```

---

## PHASE 1 — PROJECT ANALYSIS (read-only)

Read `references/project-analysis.md`, then:

1. **Inventory** the source files from the snapshot above. Separate application source code from manifests, lockfiles, docs, HTTP collections and generated files.
2. **Detect the stack** from manifests and imports: language, framework **with version** (manifest pin or lockfile), relevant dependencies.
3. **Detect the database**: engine, access style (raw SQL, ORM, query builder), connection location, and table/entity names.
4. **Find the entry point and the run command** (README, `package.json` scripts, `if __name__ == "__main__"`, `app.listen`), plus port and any setup step (e.g. seed script).
5. **Build the endpoint inventory**: every route with HTTP method, path and handler `file:line`. This list is the contract validated in Phase 3 — it must be complete.
6. **Map the current architecture**: which files hold routing, HTTP handling, business rules, data access, configuration; classify it using the categories in the reference.
7. **Infer the domain** from entities, routes, seed data and README.

Print the Phase 1 block exactly as defined in `references/report-template.md` → "Phase 1 output". Continue straight to Phase 2 in the same turn (no confirmation needed here).

## PHASE 2 — ARCHITECTURE AUDIT (read-only)

Read `references/anti-patterns-catalog.md` and `references/report-template.md`, then:

1. **Scan** every application source file against **every** catalog entry, using its detection signals (run the grep patterns, then read the surrounding code). Do not stop at the first hits: legacy code usually has issues in every layer.
2. **Verify** each candidate by reading the exact lines. Discard false positives (see each entry's "Not a finding when").
3. **Classify** with the catalog's severity rules (CRITICAL, HIGH, MEDIUM, LOW). When in doubt between two levels, use the definitions at the top of the catalog.
4. **Consolidate**: one finding per anti-pattern per root cause; when the same anti-pattern repeats, list every location in the `File:` line instead of creating near-duplicate findings.
5. **Deprecated APIs and vulnerable dependencies** — always do both checks:
   - *Code*: compare the APIs used in the code with the dependency versions detected in Phase 1 using the catalog's deprecated-API table (AP-18).
   - *Dependencies*: run the read-only dependency audit for **every** manifest, as described in AP-18 → "Dependency audit" (e.g. `npm audit --package-lock-only`; the PyPI JSON API `vulnerabilities` field for each pinned Python package). If the registry cannot be reached, write that in the report instead of assuming there are no issues.

   Report what you find as AP-18 findings and in the report's "Deprecated APIs" table (write `None detected` only when both checks came back clean).
6. **Sort** findings CRITICAL → HIGH → MEDIUM → LOW; inside a severity, by file path then line.
7. **Print** the report exactly in the "Phase 2 audit report" format (raw Markdown, not wrapped in an outer code fence), with correct counters (the summary counts must equal the findings listed).
8. **Ask for confirmation** by printing, as the very last line of your message:

   `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`

   If the snapshot shows uncommitted changes, add one line before the question recommending a commit/backup first. Then **STOP and wait for the user's answer**. Do not call any tool after asking.

## PHASE 3 — REFACTORING (only after explicit confirmation)

Read `references/mvc-guidelines.md`, `references/refactoring-playbook.md` and `references/validation-guide.md`, then execute the steps below in order. Track them with a task list when that tool is available; otherwise announce each step as you start it.

### 3.1 Baseline (before changing any project file)
Following the validation guide: prepare the runtime (virtualenv / `npm install`), boot the **original** app, run the smoke test covering **every endpoint of the Phase 1 inventory** and store the baseline results **outside the project** (e.g. `${TMPDIR:-/tmp}/refactor-arch/<project-name>/`). Stop the server. If the original app cannot boot, record the reason — that becomes the first thing to fix.

### 3.2 Plan
- Choose the target layout from the guidelines for the detected stack.
- Map **every** Phase 2 finding to a playbook transformation (`T-xx`).
- Adapt to the starting point:
  - **Monolith / flat files** → build the full layer structure and split code by domain.
  - **Partially layered** (folders already exist) → keep what is already correct, move modules into the canonical layers, extract the missing layers (controllers, config, error handling) and thin out fat routes. Do not rewrite working code without a finding that justifies it.

### 3.3 Execute (in this order)
1. `config/` — settings from environment variables, safe defaults, no secrets in code; add `.env.example`.
2. `models/` — database connection/session and entities/data access with parameterized queries; domain rules that belong to an entity.
3. `services/` — only for use cases spanning several models or external side effects (payment, e-mail, notifications).
4. `controllers/` — request flow: read input → validate → call model/service → choose status and view.
5. `views/` — route registration (URL + method → controller) and response serializers.
6. `middlewares/` — centralized error handler and guards required by the contract exceptions.
7. Composition root / entry point — app factory wiring everything; keep the original start command working.
8. Remove the old modules that were fully migrated, dead code and unused imports; update dependency manifests only when needed; update the project README run instructions if anything changed.

### 3.4 Validate
Boot the refactored app and rerun the same smoke test. Compare with the baseline following the validation guide. Fix every regression and repeat until all endpoints match (differences allowed only for the documented contract exceptions).

### 3.5 Re-audit
Rerun the catalog detection signals on the new code. Any remaining CRITICAL or HIGH finding must be fixed now; anything intentionally left (e.g. needs a product decision such as introducing authentication) must be listed as a remaining item with the reason.

### 3.6 Clean up
Stop every process you started, delete runtime artifacts you created inside the project that are not versioned (database files, logs, `__pycache__`), and keep dependency folders out of version control.

### 3.7 Report
Print the "Phase 3 output" block from `references/report-template.md`: new structure tree, finding → transformation mapping, contract changes, validation results (only checks actually executed, with ✓ or ✗) and remaining items.

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| Pinned dependency fails to install | Runtime newer/older than the pins | Try the closest compatible patch/minor version; record the change in the Phase 3 summary |
| `Could not locate the bindings file` (Node native module) | Recent npm versions block install scripts not listed in `allowScripts` | `npm install-scripts approve <pkg>` (writes `allowScripts` to `package.json`) then `npm rebuild <pkg>` |
| `Address already in use` | Port busy (often a server you left running) | Stop your previous process group; otherwise run on a free port via the new config (`PORT=...`) |
| Server keeps running after kill (Flask) | Debug reloader spawns a child process | Start with debug/reloader disabled or kill the whole process group |
| `ImportError` / circular import after moving files | Modules importing the app instance or each other | Use the app factory; import models inside the composition root; pass dependencies as parameters |
| Endpoint returns 404 after refactor | Blueprint/router not registered or prefix changed | Compare the route table with the Phase 1 inventory |
| Fewer than 5 findings | Scan stopped too early | Re-run every catalog signal on every file, including config, seed and helper modules |
