# Output Templates

The templates are **Markdown that reads well both in the terminal and when saved as a `.md` file**. Print them as raw Markdown in your message — do **not** wrap a whole report in an outer code fence (the banners already have their own fences). Fixed labels, banners (`================================`, 32 `=`) and section names must be printed **exactly** as below; replace `<...>` placeholders. Free text follows the language rule in SKILL.md.

---

## Phase 1 output

The whole Phase 1 block goes inside one `text` code fence (column alignment matters):

````
```text
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language> [<runtime version if declared>]
Framework:     <framework> <version>
Dependencies:  <other runtime dependencies with versions, comma separated | none>
Domain:        <domain description (main entities)>
Architecture:  <category> — <short justification, max ~120 characters>
Source files:  <N> files analyzed (~<LOC> lines of code)
Database:      <engine> via <driver/ORM> (<file/memory/URI>)
DB tables:     <table1>, <table2>, ...
Entry point:   <file> → <start command> (port <port>)
Endpoints:     <N> routes
  <METHOD> <path>  → <handler> (<file>:<line>)
  ...
================================
```
````

Rules:
- `Framework` version comes from the manifest/lockfile.
- The endpoint list must contain every route (it is reused in Phase 3).

---

## Phase 2 audit report

This block is the artifact users save as the audit report (e.g. `reports/audit-<project>.md`). Print it in full, inside the message (never only in a file).

````
```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project directory name>
Stack:   <Language> + <Framework> <version>
Files:   <N> analyzed | ~<LOC> lines of code
```

## Summary

CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <Anti-pattern name>
- **ID:** <AP-xx>
- **File:** `<path>:<line or start-end>`[, `<path>:<line>`, ...]
- **Description:** <what is wrong, citing the concrete code (function, variable, literal)>
- **Impact:** <consequence for security, correctness, maintainability or performance>
- **Recommendation:** <concrete fix> (Playbook <T-xx>)

### [HIGH] <Anti-pattern name>
- **ID:** ...
- **File:** ...
- **Description:** ...
- **Impact:** ...
- **Recommendation:** ...

<... all findings, ordered CRITICAL → HIGH → MEDIUM → LOW ...>

## Deprecated APIs

| Location | Deprecated API / dependency | Modern replacement |
|---|---|---|
| `<path>:<line>` | <api or package@version and why> | <replacement> |

<or the single line: None detected>

```text
================================
Total: <N> findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````

Rules:
1. `Summary` counters must match the number of `### [SEVERITY]` headings; `Total` = sum.
2. One heading per finding: `### [<SEVERITY>] <Anti-pattern name>`. When the same anti-pattern has distinct root causes with different severities, create separate findings with a distinguishing suffix (e.g. `Unprotected Destructive Endpoints — raw SQL execution`).
3. `File:` uses paths relative to the project root and **verified** line numbers, each location in backticks. Ranges use `start-end`. Several locations are comma separated; no "etc.", no "...".
4. `Description` must quote the concrete evidence (function name, literal, query) so the reader can find it without opening the file. Keep each field in a single bullet (sub-bullets allowed for lists of cases).
5. Ordering: severity (CRITICAL, HIGH, MEDIUM, LOW), then file path, then first line.
6. Deprecated APIs appear both as findings (AP-18) and in the table.
7. The confirmation question is the **last line of the message**, outside any code fence.

### Example finding (format reference)

```markdown
### [CRITICAL] SQL Injection
- **ID:** AP-02
- **File:** `repository.py:28`, `repository.py:47-50`, `repository.py:109-111`
- **Description:** Queries are built by string concatenation with request data, e.g. `"SELECT * FROM accounts WHERE email = '" + email + "'"` in `find_by_login()`.
- **Impact:** Authentication bypass and full database read/write through crafted input (e.g. `email = ' OR 1=1 --`).
- **Recommendation:** Use driver placeholders (`?`) and pass values as parameters; keep SQL only in the model layer. (Playbook T-02)
```

---

## Phase 3 output

````
```text
================================
PHASE 3: REFACTORING COMPLETE
================================
```

## New Project Structure

```text
<tree of the new layout, application files only, with one-line role comments for key files>
```

## Findings Addressed

| Finding | Severity | Status | Transformation | Where it was fixed |
|---|---|---|---|---|
| <AP-xx name> | <SEV> | Fixed / Partially fixed / Not fixed | <T-xx> | `<new file(s)>` |

## Contract Changes

- <METHOD path> — <what changed and why> (or: None)

## How to Run

```bash
<setup and start commands, required environment variables>
```

## Validation

```text
  ✓ Application boots without errors (<command>, port <port>)
  ✓ All endpoints respond correctly (<passed>/<total> checks match the baseline)
  ✓ <each additional check actually executed, e.g. SQL injection payload returns empty result>
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-audit)
  ✗ <any check that failed, with the reason>
```

## Remaining Items

- <item intentionally not changed and why> (or: None)

```text
================================
```
````

Rules:
- Only print ✓ for checks you actually executed in this session and that passed; use ✗ otherwise.
- The endpoint count must match the Phase 1 inventory; list any mismatch explicitly.
- **Every finding of the Phase 2 report appears in "Findings Addressed"**, with the same name and severity, and with an explicit status. The number of rows equals the number of findings.
- `Partially fixed` and `Not fixed` rows must name, in "Remaining Items", exactly what is missing and which contract rule blocks it. A finding may only stay unfixed when the fix is outside the allowed exceptions of `mvc-guidelines.md` §9.
