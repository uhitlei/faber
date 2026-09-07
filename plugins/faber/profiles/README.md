# Perfis — presets de `faber/config/faber.env`

Um perfil é um trecho de configuração que o `install.sh --profile <nome>`
aplica por cima dos defaults (as respostas interativas ainda prevalecem).
Copie e adapte à vontade; o formato é o mesmo do `faber.env`.

| Perfil | Para quê |
|---|---|
| `generic.env` | qualquer stack; só o núcleo (sem módulos) |
| `node-web.env` | app web Node/TypeScript com Playwright |
| `node-supabase.env` | Node + Supabase (migrations com RLS, refs de ambientes, comandos remotos com confirmação) |
| `python.env` | projeto Python (ruff/pytest) |
