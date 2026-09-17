# Output Templates

Fixed labels, separators (`================================`, 32 `=`) and section names must be printed **exactly** as below. Replace `<...>` placeholders. Free text follows the language rule in SKILL.md.

---

## Phase 1 output

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language> [<runtime version if declared>]
Framework:     <framework> <version>
Dependencies:  <other runtime dependencies, comma separated | none>
Domain:        <domain description (main entities)>
Architecture:  <category> — <one-line justification>
Source files:  <N> files analyzed (~<LOC> lines of code)
Database:      <engine> via <driver/ORM> (<file/memory/URI>)
DB tables:     <table1>, <table2>, ...
Entry point:   <file> → <start command> (port <port>)
Endpoints:     <N> routes
  <METHOD> <path>  → <handler> (<file>:<line>)
  ...
================================
```

Rules:
- `Framework` version comes from the manifest/lockfile.
- The endpoint list must contain every route (it is reused in Phase 3).

---

## Phase 2 audit report

This block is the artifact users save as the audit report. Print it in full, inside the message (not only in a file).

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project directory name>
Stack:   <Language> + <Framework> <version>
Files:   <N> analyzed | ~<LOC> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <Anti-pattern name>
ID: <AP-xx>
File: <path>:<line or start-end>[, <path>:<line>, ...]
Description: <what is wrong, citing the concrete code (function, variable, literal)>
Impact: <consequence for security, correctness, maintainability or performance>
Recommendation: <concrete fix> (Playbook <T-xx>)

### [HIGH] <Anti-pattern name>
ID: <AP-xx>
File: ...
Description: ...
Impact: ...
Recommendation: ...

... (all findings, ordered CRITICAL → HIGH → MEDIUM → LOW)

## Deprecated APIs
| Location | Deprecated API | Modern replacement |
|---|---|---|
| <path>:<line>[, ...] | <api> | <replacement> |

(or the single line: None detected)

================================
Total: <N> findings
================================
```

Rules:
1. `Summary` counters must match the number of `### [SEVERITY]` headings; `Total` = sum.
2. One heading per finding: `### [<SEVERITY>] <Anti-pattern name>`. When the same anti-pattern has distinct root causes with different severities, create separate findings with a distinguishing suffix (e.g. `Unprotected Destructive Endpoints — raw SQL execution`).
3. `File:` uses paths relative to the project root and **verified** line numbers. Ranges use `start-end`. Several locations are comma separated; no "etc.", no "...".
4. `Description` must quote the concrete evidence (function name, literal, query) so the reader can find it without opening the file.
5. Ordering: severity (CRITICAL, HIGH, MEDIUM, LOW), then file path, then first line.
6. Deprecated APIs appear both as findings (AP-18) and in the table.
7. After the closing separator, print (as the last line of the message):
   `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`

### Example finding (format reference)

```
### [CRITICAL] SQL Injection
ID: AP-02
File: repository.py:28, repository.py:47-50, repository.py:109-111
Description: Queries are built by string concatenation with request data, e.g. "SELECT * FROM accounts WHERE email = '" + email + "'" in find_by_login().
Impact: Authentication bypass and full database read/write through crafted input (e.g. email = ' OR 1=1 --).
Recommendation: Use driver placeholders (?) and pass values as parameters; keep SQL only in the model layer. (Playbook T-02)
```

---

## Phase 3 output

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<tree of the new layout, application files only, with one-line role comments for key files>

## Findings Addressed
| Finding | Severity | Transformation | Where it was fixed |
|---|---|---|---|
| <AP-xx name> | <SEV> | <T-xx> | <new file(s)> |

## Contract Changes
- <endpoint> — <what changed and why> (or: None)

## How to Run
<setup and start commands, required environment variables>

## Validation
  ✓ Application boots without errors (<command>, port <port>)
  ✓ All endpoints respond correctly (<passed>/<total> checks match the baseline)
  ✓ <each additional check actually executed, e.g. SQL injection payload returns empty result>
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (re-audit)
  ✗ <any check that failed, with the reason>

## Remaining Items
- <item intentionally not changed and why> (or: None)
================================
```

Rules:
- Only print ✓ for checks you actually executed in this session and that passed; use ✗ otherwise.
- The endpoint count must match the Phase 1 inventory; list any mismatch explicitly.
