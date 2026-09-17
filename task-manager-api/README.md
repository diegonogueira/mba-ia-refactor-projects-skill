# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. O código segue MVC: `src/models` (entidades, consultas e regras de domínio), `src/views` (rotas e serializers), `src/controllers` (fluxo das requisições e validação), `src/services` (relatórios e autenticação), `src/middlewares` (tratamento central de erros) e `src/config` (configuração por variáveis de ambiente).

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Configuração

As variáveis de ambiente estão documentadas em `.env.example`:

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | valor aleatório efêmero (com aviso no log) | Assinatura dos tokens de login — defina em produção |
| `FLASK_DEBUG` | `false` | Debugger/reloader do Flask |
| `HOST` | `127.0.0.1` | Use `0.0.0.0` para aceitar conexões de outras máquinas |
| `PORT` | `5000` | Porta HTTP |
| `DATABASE_URL` | `sqlite:///tasks.db` | URL do SQLAlchemy |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula |
| `LOG_LEVEL` | `INFO` | Nível de log |
