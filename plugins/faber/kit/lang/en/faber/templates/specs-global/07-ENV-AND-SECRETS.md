# 07 · Environments & secrets

## 1. Environment variables (by NAME — never values)

| Variable | Environment(s) | Purpose | Where it is defined |
|---|---|---|---|
| {{APP_URL}} | {{local/staging/prod}} | {{...}} | {{.env.local / CI secrets / the provider's panel}} |

## 2. Environment files

- `{{.env.example}}` — versioned, names and example values only.
- `{{.env, .env.local}}` — **never versioned, never edited by an agent**
  (H2: `FABER_SECRET_FILES`).

## 3. Remote environment refs

| Environment | Identifier (ref) | Regime for agents |
|---|---|---|
| production | {{ref}} | **forbidden** (`FABER_REFS_DENY`) |
| staging | {{ref}} | **confirmation per execution** (`FABER_REFS_CONFIRM`) |
| local | 127.0.0.1 | autonomous |

## 4. Rotation and access

- {{who has access; how to rotate; where it is recorded}}

## 5. External tools (by variable name)

- {{SONAR_TOKEN / SONAR_HOST_URL (when FABER_SONAR=on)}}
- {{GITHUB_TOKEN (an authenticated gh CLI)}}
