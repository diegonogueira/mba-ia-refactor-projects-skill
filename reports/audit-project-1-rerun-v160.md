# Audit Report — code-smells-project (3ª reauditoria pós-avaliação, skill v1.6.0)

> Saída **verbatim** da Fase 2 da skill `refactor-arch` (v1.6.0), gerada por `claude -p "/refactor-arch"` dentro de `code-smells-project/`
> (modelo `claude-opus-5-5`, Claude Code 2.1.282, sessão `eead10e7-c8e9-4b7d-a1ec-0578e23f05a4`). Nenhuma edição manual no conteúdo abaixo.
> Contagem conferida automaticamente: CRITICAL 1 · HIGH 0 · MEDIUM 0 · LOW 1 · Total 2.
> Esta é a execução que produziu o código versionado do projeto 1. Ela audita o código já refatorado, por isso sobram poucos findings; o relatório do código legado é o [`audit-project-1.md`](audit-project-1.md) (26 findings).

---

```text
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.3
Files:   35 analyzed | ~1239 lines of code
```

## Summary

CRITICAL: 1 | HIGH: 0 | MEDIUM: 0 | LOW: 1

## Findings

### [CRITICAL] Unprotected Management Endpoints — login issues no credential
- **ID:** AP-06
- **File:** `src/controllers/usuario_controller.py:32-39`, `src/views/serializers.py:4`, `src/views/pedido_routes.py:8-14`, `src/views/produto_routes.py:10-12`, `src/views/relatorio_routes.py:7`, `src/views/usuario_routes.py:7-8`
- **Description:** `login()` confere a senha, mas só devolve `serializar_login(usuario)`. Esse serializer tem os campos `CAMPOS_USUARIO_LOGIN = ("id", "nome", "email", "tipo")` e nenhum token, sessão ou credencial assinada. Por isso nenhuma rota consegue saber quem está chamando. As rotas de gestão são registradas com `add_url_rule` sem nenhum guard. As que alteram dados são `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>` e `PUT /pedidos/<id>/status`. As que listam dados de terceiros são `GET /usuarios`, `GET /pedidos` e `GET /relatorios/vendas`. Os recursos de um único dono são `GET /usuarios/<id>` e `GET /pedidos/usuario/<id>`. Só `/admin/*` tem proteção (`admin_only`, desligado por padrão, com token por `hmac.compare_digest`). A coluna `tipo` (`admin`/`cliente`) existe no banco, mas nenhuma rota a usa para autorização.
- **Impact:** Qualquer cliente anônimo na rede pode:
  - alterar preço e estoque de qualquer produto e apagar produtos do catálogo;
  - aprovar, marcar como entregue ou cancelar pedidos de outras pessoas (o cancelamento devolve estoque e fecha o pedido num estado final irreversível);
  - baixar a lista completa de usuários com e-mail e papel;
  - ler os pedidos de qualquer usuário, trocando o id na URL (IDOR);
  - ler o faturamento da loja em `/relatorios/vendas`.
- **Recommendation:** Implementar autenticação com papéis (Playbook T-06, "Authentication for management routes"; §9 exceção 11):
  - (1) `POST /login` mantém rota, status e campos e **passa a incluir** um token assinado e com expiração. O token é gerado com `itsdangerous.URLSafeTimedSerializer` e `SECRET_KEY` e carrega só o id do usuário. O papel é lido do banco a cada requisição, nunca do token nem do corpo.
  - (2) Um middleware `auth_guard` lê `Authorization: Bearer <token>`. Sem token ou com token inválido/expirado, responde 401. Com token válido mas sem o papel exigido, responde 403. Os dois erros usam o envelope `{"erro", "sucesso": false}`.
  - (3) Papel `admin` exigido em `POST/PUT/DELETE /produtos`, `PUT /pedidos/<id>/status`, `GET /usuarios`, `GET /pedidos` e `GET /relatorios/vendas`.
  - (4) Dono do recurso ou `admin` exigido em `GET /usuarios/<id>` e `GET /pedidos/usuario/<id>`.
  - (5) Continuam públicas as leituras da vitrine (`GET /produtos*`), o cadastro, o login, `/`, `/health` e `POST /pedidos` (ação do próprio cliente).
  - (6) Com o papel correto, a resposta é idêntica à original. O README deve explicar como obter e enviar o token.

### [LOW] Magic Strings — user roles
- **ID:** AP-20
- **File:** `src/models/database.py:34`, `src/models/database.py:69-71`, `src/models/usuario_model.py:9`
- **Description:** Os papéis de usuário aparecem como literais soltos. Os literais são `'cliente'` no `DEFAULT` do schema, `"admin"`/`"cliente"` nas tuplas de `USUARIOS_SEED` e `TIPO_PADRAO = "cliente"` em `usuario_model`. Não existe constante para `"admin"`.
- **Impact:** O guard de papéis recomendado acima vai comparar `tipo == "admin"`. Se o literal for digitado de novo em outro módulo, um erro de grafia entre o seed e o guard deixa o admin sem acesso ou abre uma brecha, e nenhum erro aparece.
- **Recommendation:** Definir `TIPO_ADMIN` e `TIPO_CLIENTE` em `usuario_model` e usar essas constantes no seed, no default de criação e no novo guard de autorização (Playbook T-15).

## Deprecated APIs

None detected

> Verificações feitas: (1) as APIs do código foram comparadas com a tabela AP-18 para Python 3.14, Flask 3.1 e Werkzeug 3.1, com grep de `utcnow`, `before_first_request`, `__version__`, `url_quote/url_parse`, `detect_types`, `pkg_resources` e `distutils`, sem nenhuma ocorrência; (2) o campo `vulnerabilities` da API JSON do PyPI veio vazio para `flask==3.1.3`, `flask-cors==6.0.5` e `werkzeug==3.1.8`, e as três já são a versão mais recente. Observação de reprodutibilidade: as dependências transitivas do Flask (`itsdangerous`, `jinja2`, `click`, `blinker`, `markupsafe`) não estão fixadas.

```text
================================
Total: 2 findings
================================
```

Esta é uma reauditoria de um código que já está em camadas MVC. Os problemas das rodadas anteriores continuam corrigidos: SQL parametrizado, hashes de senha, `/admin/*` fechado por padrão, estoque devolvido uma única vez ao cancelar, transações e error handler central. Descartei dois falsos positivos. Os f-strings de SQL só interpolam constantes, então não são AP-02. A senha sorteada do seed aparece uma vez no log, que é exatamente a correção permitida pela §9 exceção 8. O problema grave que sobra é a falta de autenticação nas rotas de gestão.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
