# 07 · Ambientes & Secrets

## 1. Variáveis de ambiente (por NOME — nunca valores)

| Variável | Ambiente(s) | Propósito | Onde é definida |
|---|---|---|---|
| {{APP_URL}} | {{local/hml/prod}} | {{...}} | {{.env.local / secrets do CI / painel}} |

## 2. Arquivos de ambiente

- `{{.env.example}}` — versionado, só nomes e valores de exemplo.
- `{{.env, .env.local}}` — **nunca versionados, nunca editados por agente** (H2: `FABER_SECRET_FILES`).

## 3. Refs de ambientes remotos

| Ambiente | Identificador (ref) | Regime para agentes |
|---|---|---|
| produção | {{ref}} | **proibido** (`FABER_REFS_DENY`) |
| homologação | {{ref}} | **confirmação por execução** (`FABER_REFS_CONFIRM`) |
| local | 127.0.0.1 | autônomo |

## 4. Rotação e acesso

- {{quem tem acesso; como rotacionar; onde registrar}}

## 5. Ferramentas externas (por nome de variável)

- {{SONAR_TOKEN / SONAR_HOST_URL (se FABER_SONAR=on)}}
- {{GITHUB_TOKEN (gh CLI autenticado)}}
