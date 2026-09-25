# Audit Report — task-manager-api (reauditoria final, skill v1.6.1)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.6.1), gerada por `claude -p "/refactor-arch"` dentro de `task-manager-api/`
> (modelo `claude-opus-5-5`, Claude Code 2.1.282, sessão `468fded8-4c8d-41d8-a8f8-4f625ece81da`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 1 · HIGH 0 · MEDIUM 2 · LOW 0 · Total 3.
> Esta execução produziu o código versionado do projeto. Ela audita o código já refatorado, por isso sobram poucos findings; o relatório do código legado é o [`audit-project-3.md`](audit-project-3.md).

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.1.3
Files:   40 analyzed | ~1676 lines of code
```

## Summary

CRITICAL: 1 | HIGH: 0 | MEDIUM: 2 | LOW: 0

## Findings

### [CRITICAL] Broken Authentication — management routes are anonymous
- **ID:** AP-06
- **File:** `src/services/auth_service.py:25-26`, `src/views/task_routes.py:8`, `src/views/task_routes.py:12-13`, `src/views/user_routes.py:9`, `src/views/user_routes.py:11-12`, `src/views/user_routes.py:16-17`, `src/views/category_routes.py:8-12`, `src/views/report_routes.py:7-8`, `src/controllers/user_controller.py:39-47`
- **Description:** `POST /login` issues a signed token (`AuthService.issue_token` → `self._serializer.dumps({'user_id': user.id})`), but nothing in the code ever reads it: there is no `loads`, no `Authorization` header check, and no guard other than `admin_only` on `DELETE /users/<id>`. The README admits it (`README.md:100-103`, "nenhuma rota exige autenticação"). The affected routes, all anonymous today, are:
  - **Account takeover:** `PUT /users/<id>` (`update_user`) changes the `email` and `password` of any id.
  - **Destroys shared data:** `POST/PUT/DELETE /tasks[/<id>]` (including `user_id` chosen by the client) and `POST/PUT/DELETE /categories[/<id>]`.
  - **Exposes personal data:** `GET /users` (every user's e-mail and role), `GET /users/<id>`, `GET /users/<id>/tasks` and the `GET /reports/summary` and `GET /reports/user/<id>` reports.
- **Impact:** Any client on the network can take over any account, including the seeded admin (it swaps the password and then logs in). It can also delete or rewrite any task or category, create tasks in someone else's name, and list every user's e-mail and productivity. The token has no expiration because it is never validated.
- **Recommendation:** Keep `POST /login` as it is (it already returns `token`) and add verification of the token with an expiration (`URLSafeTimedSerializer.loads(max_age=...)`). The role is read from the database on each request. Add `middlewares/auth_guard` guards (401 without a token or with an invalid/expired one, 403 without permission):
  - **`admin` role:** `GET /users`, `POST/PUT/DELETE /categories`, `GET /reports/summary`.
  - **Owner or admin:** `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>`.
  - **Tasks:** `POST /tasks` and `PUT /tasks/<id>` require a token, and the `user_id` sent must be the caller's own (or the caller is an admin). `PUT/DELETE /tasks/<id>` on a task that has an owner → owner or admin.
  - **Stay public:** `GET /`, `/health`, task and category reads, `POST /users` (sign-up) and `POST /login`.
  - **Unchanged:** `DELETE /users/<id>` keeps the current administrative guard (flag + `X-Admin-Token`, exception 2).
  - Document it in the README. (Playbook T-06)

### [MEDIUM] Inconsistent Input Validation — create vs update
- **ID:** AP-14
- **File:** `src/controllers/validators/user_validator.py:64-65`, `src/controllers/validators/user_validator.py:88-89`, `src/controllers/validators/category_validator.py:38-39`, `src/controllers/validators/category_validator.py:53-54`, `src/utils/validators.py:17-23`
- **Description:** On create, `validate_new_user`/`validate_new_category` reject an empty name (`if not name: raise ValidationError(NAME_REQUIRED_MESSAGE)`). On update, `validate_user_changes`/`validate_category_changes` only call `_name(data['name'])` → `validate_bounded_text`, which checks type and maximum length but accepts `""` and whitespace-only strings (the latter are accepted on create too).
- **Impact:** `PUT /users/<id>` with `{"name": ""}` and `PUT /categories/<id>` with `{"name": "   "}` return 200 and store users and categories with no name. The name then shows up empty in `/tasks` (`user_name`/`category_name`) and in the reports.
- **Recommendation:** Centralize "required name" in `_name` (reject empty or blank after `strip()` with `NAME_REQUIRED_MESSAGE`, 400) and use it on both create and update, for users and categories. (Playbook T-12)

### [MEDIUM] Duplicated Code — per-entity queries and controller lookups
- **ID:** AP-16
- **File:** `src/models/category_model.py:33-47`, `src/models/user_model.py:62-64`, `src/models/user_model.py:70-72`, `src/models/user_model.py:79-85`, `src/models/task_model.py:102-104`, `src/controllers/category_controller.py:42-47`, `src/controllers/task_controller.py:63-68`, `src/controllers/user_controller.py:64-69`
- **Description:** `get_by_id` (`db.session.get(cls, id)`), `exists`, `list_all` (`select(cls).order_by(cls.id)`) and `count_all` are reimplemented almost identically in `Category`, `User` and `Task`, even though a shared `PersistableMixin` already exists in `src/models/database.py`. The three controllers repeat the same `_find` (get → `if None: raise NotFoundError(<message>)` → return), changing only the message.
- **Impact:** Every query or not-found rule change has to be made in three places, and the copies drift apart (e.g. `Task.list_all` already takes a different parameter).
- **Recommendation:** Move `get_by_id`, `exists`, `list_all` and `count_all` into `PersistableMixin`, plus a `get_or_404` that uses a per-entity `NOT_FOUND_MESSAGE` class attribute. `Task` keeps only its `list_all(with_relations=...)` override, and the controllers call `Model.get_or_404(id)`. (Playbook T-13)

## Deprecated APIs

None detected. In the code, no API from the table applies (`datetime.utcnow()` was already replaced by `utcnow_naive()` in `src/utils/datetime_utils.py:11`; there is no `Query.get`). For the dependencies, all 7 pins were checked against the PyPI JSON API, with 0 vulnerabilities and no yanked versions. Note: `sqlalchemy` 2.1.1 is available, but 2.0.54 is still supported and not vulnerable.

```text
================================
Total: 3 findings
================================
```

This project was already migrated to MVC by an earlier run, so there are few findings. The remaining critical issue is authentication on the management routes, which the new skill version requires implementing.

There are uncommitted changes in the repository (skill files). I recommend committing or backing them up before Phase 3.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
