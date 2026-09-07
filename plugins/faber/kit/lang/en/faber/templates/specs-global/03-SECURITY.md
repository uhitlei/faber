# 03 · Security

## 1. Threat model (summary)

| Asset | Threat | Control |
|---|---|---|
| {{user data}} | {{improper access}} | {{RLS/ACL, authentication}} |

## 2. Authentication and authorization

- **Identity:** {{the provider, sessions, tokens}}
- **Roles:** {{where they live, how they are checked — a function, a decorator, a policy}}
- **The rule:** authorization always on the server or in the database; never in
  the client alone.

## 3. Untouchable invariants

<!-- A closed list of what NO agent changes without the Owner's explicit review.
     db-guardian, code-reviewer and migration-safe all read THIS section. -->
| Invariant | Where it lives | Why |
|---|---|---|
| {{e.g. the role function `has_role`}} | {{path}} | {{privilege escalation}} |
| {{e.g. a sensitive field only through a masked RPC}} | {{path}} | {{data leakage}} |

## 4. Sensitive data and privacy

- {{classification; masking; retention; the applicable data-protection regime}}

## 5. Secrets

- Always by **name** (`{{API_TOKEN}}`), through an environment variable; never
  in a versioned file, a log or the chat.
- Secret files protected by H2: `{{FABER_SECRET_FILES}}`.

## 6. Exposed surface

| Surface | Protection |
|---|---|
| {{the public API}} | {{rate limiting, input validation, CORS}} |

## 7. Security review checklist

- [ ] Input validated (type, size, encoding)
- [ ] Authorization checked on the server
- [ ] No secret in code or logs
- [ ] Sensitive data masked on the way out
- [ ] New dependencies audited
