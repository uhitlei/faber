# 03 · Segurança

## 1. Modelo de ameaças (resumo)

| Ativo | Ameaça | Controle |
|---|---|---|
| {{dados de usuário}} | {{acesso indevido}} | {{RLS/ACL, autenticação}} |

## 2. Autenticação e autorização

- **Identidade:** {{provedor, sessões, tokens}}
- **Papéis:** {{onde vivem, como são checados — função/decorator/policy}}
- **Regra:** autorização sempre no servidor/banco; nunca só no cliente.

## 3. Invariantes intocáveis

<!-- Lista fechada do que NENHUM agente altera sem revisão explícita do Owner.
     db-guardian, code-reviewer e migration-safe leem ESTA seção. -->
| Invariante | Onde vive | Por quê |
|---|---|---|
| {{ex.: função de papéis `has_role`}} | {{path}} | {{escalação de privilégio}} |
| {{ex.: campo sensível só via RPC mascarada}} | {{path}} | {{vazamento de dado}} |

## 4. Dados sensíveis e privacidade

- {{classificação; mascaramento; retenção; LGPD/GDPR}}

## 5. Secrets

- Sempre por **nome** (`{{API_TOKEN}}`), via variável de ambiente; nunca em arquivo versionado, log ou chat.
- Arquivos de secrets protegidos pelo H2: `{{FABER_SECRET_FILES}}`.

## 6. Superfície exposta

| Superfície | Proteção |
|---|---|
| {{API pública}} | {{rate limit, validação de entrada, CORS}} |

## 7. Checklist de review de segurança

- [ ] Entrada validada (tipo, tamanho, encoding)
- [ ] Autorização verificada no servidor
- [ ] Nenhum secret em código/log
- [ ] Dados sensíveis mascarados na saída
- [ ] Dependências novas auditadas
