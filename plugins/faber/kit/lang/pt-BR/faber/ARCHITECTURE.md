# Fábrica de Software com Agentes — @@FABER_PROJECT@@

> **Versão do kit:** 1.0.0 · Arquitetura de referência portátil, derivada de uma
> fábrica operada em produção (versão 1.1 do projeto de origem) e generalizada.
> **Configuração deste projeto:** `faber/config/faber.env`. Aprovador humano:
> **@@FABER_OWNER_NAME@@** (`@@FABER_OWNER@@`). Trunk: `@@FABER_TRUNK@@` ·
> produção: `@@FABER_MAIN@@`.
>
> A numeração das seções é **estável** — agentes, skills, comandos e hooks a
> citam (`§N`). Ao adaptar este documento ao projeto, edite o conteúdo, nunca
> a numeração.

---

## 1. Resumo executivo

A fábrica transforma uma solicitação em linguagem natural em uma PR pronta
para merge, passando por especificação, refinamento duplo, desenvolvimento,
review, validações paralelas e homologação local — com **evidência verificável
em cada gate** e o aprovador humano mantido em três pontos de decisão:
**Ready for Development (G1)**, **Minha Avaliação (G6)** e **Merge (G8)**.

Implementada com os mecanismos nativos do Claude Code:

- **1 orquestrador (CTO)** = a sessão principal, governada pelo `CLAUDE.md`.
- **9 subagentes especializados** (6 do fluxo padrão + 3 condicionais), contexto isolado, ferramentas e modelo por risco.
- **8 Skills** de conhecimento operacional (evidências, specs, migrations, ambiente local, E2E, análise estática, design system, consolidação).
- **12 comandos** de operação (`/faber-init`, `/faber-discovery`, `/faber-task`, `/faber-bug`, `/faber-spike`, `/faber-incident`, `/faber-status`, `/faber-resume`, `/faber-approve`, `/faber-develop`, `/faber-validate`, `/faber-pr`).
- **7 hooks determinísticos** que impõem as regras invioláveis por código, parametrizados por `faber/config/faber.env`.
- **GitHub Issues (+ board Projects v2 opcional)** como rastreamento visível; **arquivos versionados na branch da demanda** como fonte de verdade; **`@@FABER_SPECS_DIR@@/`** como destino canônico.

Princípios: contexto mínimo por agente · evidência antes de conclusão ·
separação planejamento/execução · proporcionalidade dos templates ao risco ·
mecânica sem LLM onde um script resolve.

---

## 2. Entendimento do cenário

<!-- Preenchido pelo /faber-init com fatos do projeto (stack, branches, CI,
     base de specs, operação, decisões do Owner). Até lá, vale a configuração. -->

- **Produto:** @@FABER_PROJECT@@ — {{domínio, estágio, perfis de usuário}}.
- **Stack:** {{...}}.
- **Git/CI:** `feature/* → PR → @@FABER_TRUNK@@ → @@FABER_MAIN@@`; CI: {{jobs}}.
- **Base canônica:** `@@FABER_SPECS_DIR@@/` (globais 00–08 + features).
- **Operação:** @@FABER_OWNER_NAME@@ é o aprovador único; modo de interação `FABER_INTERACTION`.

## 3. Premissas

- **P1** — O board Projects v2 (se `FABER_BOARD=on`) tem o campo Status com as 9 colunas macro (§6.1); a fábrica só gerencia issues com a label `faber`.
- **P2** — Tokens de ferramentas externas entram exclusivamente por variável de ambiente, referidos por **nome**; jamais versionados.
- **P3** — Os artefatos da demanda (spec, handoffs, evidências) são commitados na própria feature branch. Evidências > 2 MB são referenciadas, não commitadas.
- **P4** — O ambiente local (Skill `local-env`) é descartável: o agente tem autonomia total nele, sem aprovação.
- **P5** — DoD baseline = checklist pré-merge de `04-DEPLOYMENT.md §10`, estendido pelos gates da fábrica.
- **P6** — Idioma `FABER_LANG` em specs, issues, handoffs e mensagens de gate.

---

## 4. Arquitetura geral

### 4.1 Camadas

| Camada | Componente | Papel |
|---|---|---|
| **Orquestração** | Sessão principal = **CTO** (`CLAUDE.md` + comandos) | Entrada única, classificação, fluxo, subagentes, gates, consolidação, escalonamento |
| **Execução especializada** | Subagentes em `.claude/agents/` | Contexto isolado por responsabilidade; ferramentas e modelo restritos |
| **Conhecimento operacional** | Skills em `.claude/skills/` | Procedimentos carregados sob demanda |
| **Interface de operação** | Comandos em `.claude/commands/` | Pontos de entrada padronizados |
| **Enforcement determinístico** | Hooks em `.claude/hooks/` + `faber/config/faber.env` | Regras invioláveis aplicadas por código |
| **Estado e auditoria** | `faber/tasks/TASK-XXX/` (na branch) + Issue + board | `state.yaml` = fonte máquina; issue = espelho humano; board = kanban |
| **Destino canônico** | `@@FABER_SPECS_DIR@@/` | Consolidação final pelo doc-writer |

### 4.2 O nome "CTO"

Comunica autoridade de gate e delegação — exatamente o comportamento desejado — e é curto para comandos.

### 4.3 Por que o CTO não é um subagente

Subagentes são invocados pela sessão principal e **não invocam outros subagentes**. Logo, o orquestrador precisa ser a sessão principal: (a) o `CLAUDE.md` é a sua constituição; (b) todo paralelismo é disparado pelo CTO; (c) subagentes devolvem handoffs em arquivo e o CTO decide o próximo passo. Isso elimina, por construção, loops entre agentes fora do controle do orquestrador.

### 4.4 Estratégia Git

Modelo recomendado: **GitHub Flow + branch de integração** (`@@FABER_TRUNK@@` = homologação contínua; `@@FABER_MAIN@@` = produção, só por promoção). Regras da fábrica: produção só recebe merges vindos do trunk; o G7 verifica que a feature branch está atualizada com o trunk antes da PR. Se o projeto usa trunk único (`FABER_TRUNK=main`), o fluxo é o mesmo com um passo a menos.

---

## 5. Diagrama textual do fluxo

```text
OWNER ──/faber-task──▶ CTO (sessão principal, Opus)
                    │ 1. interpreta + consulta specs/ + classifica tipo (§14)
                    │ 2. cria TASK-XXX: issue (label faber) + branch feature/TASK-XXX
                    │    (em worktree próprio) + faber/tasks/TASK-XXX/{state.yaml, spec.md}
                    │ 3. seleciona o fluxo pelo tipo
                    ▼
     ┌── ESPECIFICAÇÃO ─────────────────────────────────────────────┐
     │ product-owner (Sonnet)      → spec de negócio, histórias, ACs │
     │   ∥ qa (Sonnet)             → testabilidade, cenários, matriz │
     │   ∥ product-designer (Sonnet, se UX/UI) → fluxos, estados, DS │
     │ (demanda técnica: CTO ou senior-developer especifica)         │
     └──────────────────────────────────────────────────────────────┘
                    ▼
     ┌── REFINAMENTO TÉCNICO (duplo, independente) ─────────────────┐
     │ CTO produz análise A   ∥   senior-developer (Opus) análise B │
     │ CTO compara → divergências → máx. 2 rodadas de réplica       │
     │ consenso ≥ critérios objetivos OU escala ao OWNER            │
     │ devsecops (Sonnet) → impacto pipeline/secrets/infra → tarefas│
     │ db-guardian (Opus, se banco) → pré-análise de modelo/RLS     │
     │ impacto_ui declarado no state.yaml                           │
     └──────────────────────────────────────────────────────────────┘
                    ▼
   ══ GATE G1 · READY FOR DEVELOPMENT ══ (OWNER — DoR objetiva)
                    ▼
     senior-developer (Opus): implementa só o escopo aprovado,
     testes, lint/build/test locais → evidências → commits rastreáveis
                    ▼
   ══ GATE G3 · DEVELOPED ══ (gate-check.sh confere evidências)
                    ▼
     code-reviewer (Opus, contexto limpo — só diff + spec)
     → parecer → tarefas → CTO = gate final do review (G4)
                    ▼
     ┌── VALIDAÇÕES PARALELAS ──────────────────────────────────────┐
     │ qa → E2E (se impacto_ui) + ACs + regressão + evidências      │
     │ db-guardian (se banco) → migration, RLS, GRANT, rollback     │
     │ devsecops → análise estática (Skill sonar-gate) ou CI        │
     └──────────────────────────────────────────────────────────────┘
                    ▼
   ══ GATE G5 · VALIDAÇÃO TÉCNICA ══ (tudo verde ou exceção formal)
                    ▼
     /faber-validate → ambiente local + build → roteiro de teste na issue
                    ▼
   ══ GATE G6 · MINHA AVALIAÇÃO ══ (OWNER testa e aprova)
                    ▼
     /faber-pr → CTO confere gates + branch atualizada + descrição
     consolidada (o quê/por quê/como testar/risco/rollback) → PR
                    ▼
   ══ GATE G8 · MERGE ══ (SEMPRE o OWNER, no GitHub)
                    ▼
     doc-writer (Sonnet): consolida specs/ + CHANGELOG + diagramas
     → limpa rascunhos → GATE G9 · DONE → worktree.sh clean
```

Em todos os pontos: transições gravadas em `state.yaml` + comentário na issue + coluna do board movida por script (`transition.sh`), sem consumo de LLM. Com `FABER_INTERACTION=gates`, o CTO encadeia os trechos entre gates humanos sem parar; com `step-by-step`, para ao fim de cada comando.

---

## 6. Máquina de estados

### 6.1 Três projeções do mesmo estado

1. **`state.yaml`** — fonte de verdade máquina: estado, timestamps, gates com aprovador e evidência.
2. **Issue** — espelho humano: label `state:<fino>` + comentários de gate.
3. **Board Projects v2** (opcional) — campo Status com **9 colunas macro**: `Backlog · Especificação · Ready for Dev · Em Desenvolvimento · Review & Validação · Minha Avaliação · PR Aberta · Done · Bloqueada`.

### 6.2 Estados finos e transições

| # | Estado | Coluna | Responsável | Entrada / artefatos obrigatórios | Saída / evidências |
|---|---|---|---|---|---|
| 1 | `intake` | Backlog | CTO | Solicitação recebida | Tipo classificado; ID emitido; issue + branch + pasta |
| 2 | `clarification` | Backlog | CTO → Owner | Ambiguidade crítica | Respostas registradas na spec |
| 3 | `specifying` | Especificação | PO (ou CTO/dev se técnica) | Fluxo selecionado | `spec.md` no nível do template; ACs claros; dúvidas zeradas ou escaladas |
| 4 | `refinement` | Especificação | CTO + senior-developer (+ devsecops, db-guardian) | Spec pronta | `refinement.md` (A e B, divergências resolvidas/trade-offs); tarefas DevSecOps; `ui_impact` |
| 5 | `ready-for-dev` | Ready for Dev | **Owner** (G1) | DoR 100% (§18) | Aprovação registrada (`/faber-approve`) |
| 6 | `in-development` | Em Desenvolvimento | senior-developer | G1 aprovado | Escopo implementado; testes; lint+build+test verdes (logs) |
| 7 | `developed` | Em Desenvolvimento | gate-check.sh | Evidências G3 | Push da branch |
| 8 | `code-review` | Review & Validação | code-reviewer + CTO | `developed` + branch no remoto | Parecer sem bloqueio crítico |
| 9 | `validation` | Review & Validação | qa ∥ db-guardian ∥ devsecops | G4 aprovado + `review.md` | E2E (se UI) + ACs + banco + análise estática verdes |
| 10 | `my-review` | Minha Avaliação | **Owner** (G6) | G5 verde; ambiente pronto; roteiro na issue | "TASK-XXX validada" |
| 11 | `ready-for-pr` | Minha Avaliação | CTO (G7) | G6 aprovado | Branch atualizada com o trunk; descrição de PR |
| 12 | `pr-open` | PR Aberta | **Owner** (G8) | G7 + campo `pr` | Merge feito pelo Owner no GitHub |
| 13 | `done` | Done | doc-writer (G9) | G1–G8 aprovados/n.a. | specs consolidadas; CHANGELOG; issue fechada; **branch apagada** (`worktree.sh clean`) |
| 14 | `blocked` | Bloqueada | quem bloqueou | Motivo obrigatório | Retorna ao estado de origem |
| 15 | `cancelled` | — (issue fechada) | **Owner** | Decisão explícita (`--reason`) | Motivo registrado |

**Regras gerais:** nenhuma transição sem `gate-check.sh`; regressão só com motivo; reabertura de `done` gera **nova demanda** vinculada (`related_to`); `blocked` guarda o estado de origem; toda transição = commit em `state.yaml` + comentário na issue + board.

### 6.3 Cópia autoritativa entre fontes divergentes

Uma demanda pode existir em várias cópias de `state.yaml` (worktrees ativos e refs do git). **A cópia autoritativa é a de maior `updated_at`**, varrendo todas as fontes conhecidas. Um `state` fora da lista fechada dos 15 é **leitura inválida**, nunca estado, e nunca vence de uma cópia válida. Todo leitor agregado (ex.: `faber/dashboard/`) implementa esta regra.

---

## 7. Agentes obrigatórios

| Agente | Tipo | Modelo | Responsabilidade central | Não faz | Lê | Escreve |
|---|---|---|---|---|---|---|
| **CTO** | Sessão principal | Opus | Entrada única; classificação; fluxo; subagentes; refinamento duplo (A); gates; consolidação; escalonamento | Implementar código; aprovar gates humanos | Tudo | `faber/`, issue/board (via scripts) |
| **product-owner** | Subagente | Sonnet | Spec de negócio: problema, valor, escopo, regras, histórias, ACs | Inventar regra de negócio; decidir arquitetura | specs, spec da demanda | `spec.md`, handoff |
| **senior-developer** | Subagente | **Opus** | Análise B; implementação do escopo aprovado; testes; evidências; commits | Alterar escopo; tocar migrations aplicadas/CI/trunk | specs, código, spec+refinamento | código, migrations novas, testes, evidências, handoff |
| **code-reviewer** | Subagente | **Opus** | Review de contexto limpo (diff + spec + convenções) | Corrigir código; aprovar o próprio parecer | diff, spec, 06/03 | `review.md`, tarefas |
| **qa** | Subagente | Sonnet | Fase spec: testabilidade, cenários, matriz. Validação: E2E, ACs, regressão, evidências | Afrouxar critério; validar sem executar | spec, 05-TESTING, testes | cenários na spec, testes E2E, evidências, handoff |
| **devsecops** | Subagente | Sonnet | Impacto em pipeline/secrets/infra/deploy/rollback; opera `sonar-gate` ou lê o CI | Editar workflows sem tarefa aprovada; manusear secrets | workflows, 04, 07 | tarefas na spec, evidência, handoff |
| **doc-writer** | Subagente | Sonnet | Done: consolida a spec em `@@FABER_SPECS_DIR@@/` (17 seções), CHANGELOG, diagramas | Alterar código; reescrever decisões | pasta da demanda, specs | specs, arquivamento |

**Por que um `code-reviewer` separado:** o valor do review vem do contexto limpo — o revisor não carrega o raciocínio de quem implementou. **Por que o `doc-writer`:** a base canônica exige sincronização a cada mudança — responsabilidade distinta, com contexto próprio, paralelizável após o merge.

## 8. Agentes condicionais

| Agente | Modelo | Acionado quando | Responsabilidade |
|---|---|---|---|
| **business-analyst** | **Opus** | Fontes de discovery/brainstorm e novas evidências de negócio | Evidências, requisitos, BRD/PRD, perguntas e prontidão; antes do PO (§21) |
| **db-guardian** | **Opus** | Impacto em dados/banco | Pré-análise no refinamento; na validação: migration (GRANT/RLS/policy/índices/integridade), destrutividade, compatibilidade, rollback, exposição indevida |
| **product-designer** | Sonnet | Impacto de UX/UI | Reuso do Design System, fluxos, estados de interface, responsivo, acessibilidade, tokens semânticos |

## 9. Papéis avaliados e onde vivem

| Papel | Veredito |
|---|---|
| Arquiteto | Etapa: o refinamento duplo CTO×dev **é** a função de arquitetura |
| Engenheiro de segurança | Checklist/Skill: 03-SECURITY + devsecops + db-guardian + reviewer |
| SRE/Observabilidade | Checklist do devsecops |
| Incident Commander | Comando `/faber-incident` (modo do CTO) |
| Performance | Checklist do reviewer + limites do projeto |
| Acessibilidade | Checklist do product-designer |
| Release Manager | Humano + CI (merge é do Owner) |

## 10. Matriz RACI

| Atividade | Owner | CTO | PO | Dev | Reviewer | QA | DevSecOps | DB-G | Designer | Doc |
|---|---|---|---|---|---|---|---|---|---|---|
| Classificação e triagem | I | **R/A** | — | — | — | — | — | — | — | — |
| Spec de negócio | C | A | **R** | — | — | C | — | — | C | — |
| Cenários de teste | I | A | C | — | — | **R** | — | — | — | — |
| Design UX/UI | C | A | C | — | — | — | — | — | **R** | — |
| Refinamento técnico | C* | **R/A** | — | **R** | — | — | C | C | — | — |
| G1 | **A** | R | I | I | — | I | I | I | I | — |
| Implementação | I | A | — | **R** | — | — | — | — | — | — |
| Code review | I | **A** | — | I | **R** | — | — | — | — | — |
| Validação E2E/ACs | I | A | — | I | — | **R** | — | — | — | — |
| Validação de banco | I | A | — | I | — | — | — | **R** | — | — |
| Gate de análise estática | I | A | — | I | — | — | **R** | — | — | — |
| G6 | **R/A** | I | — | — | — | — | — | — | — | — |
| PR (G7) | I | **R** | — | C | — | — | — | — | — | — |
| Merge (G8) | **R/A** | I | — | — | — | — | — | — | — | — |
| Consolidação (G9) | I | A | — | — | — | — | — | — | — | **R** |

\* Consultado apenas quando o consenso não é atingido em 2 rodadas.

---

## 11. Skills

| Skill | Usada por | Problema que resolve | Módulo |
|---|---|---|---|
| `requirements-discovery` | BA, CTO | Evidências, elicitação e documentos rastreáveis | discovery |
| `requirements-readiness` | BA, CTO, QA | Completude verificável e selo de revisão | discovery |
| `spec-task` | CTO, PO | Templates proporcionais por tipo + regras de preenchimento | núcleo |
| `evidence` | todos | Executa o comando real e grava stdout/stderr + exit code + timestamp | núcleo |
| `spec-sync` | doc-writer | Consolidação RFC (17 seções), CHANGELOG, diagramas, sem duplicar | núcleo |
| `migration-safe` | dev, db-guardian | Template de migration, destrutividade, rollback reverso | `FABER_MIGRATIONS_DIR` |
| `local-env` | dev, qa | Ambiente local descartável; valida alvo local antes de destruir | `FABER_LOCAL_ENV` |
| `e2e-runner` | qa | Execução E2E com os padrões do projeto e evidência qualificável | `FABER_E2E` |
| `sonar-gate` | devsecops, CTO | Análise estática por demanda (espelho) com veredito Critical∪High e catraca | `FABER_SONAR` |
| `design-system-check` | designer, reviewer | Grep de cor hardcoded + checklist manual | `FABER_DESIGN_SYSTEM` |

Board-sync é um script (`board.sh`), não uma Skill: zero LLM.

## 12. Comandos

| Comando | O que faz |
|---|---|
| `/faber-init` | Bootstrap: lê `faber/bootstrap/CONTEXT.md` (modo detectado pelo `install.sh`) e gera specs/config/backlog |
| `/faber-discovery TASK-XXX <fontes>` | Discovery em demanda existente; esclarecimento, BRD/PRD e handoff ao PO |
| `/faber-task <descrição>` | Entrada padrão: classifica, cria TASK-XXX (issue+branch+pasta, em worktree) e inicia o fluxo |
| `/faber-bug <descrição>` | Atalho: exige **reprodução** antes da spec |
| `/faber-incident <descrição>` | Fluxo rápido: contenção → diagnóstico → fix → post-mortem (Owner síncrono) |
| `/faber-spike <tema>` | Investigação com timebox; saída = mini-ADR |
| `/faber-status [TASK-XXX]` | Estado consolidado lido do disco + `gh` |
| `/faber-resume TASK-XXX` | Reconstrói o contexto do disco em worktree próprio e continua |
| `/faber-approve TASK-XXX <gate>` | Registra a aprovação do Owner (G1/G6/G8) e destrava a transição |
| `/faber-develop TASK-XXX` | Pós-G1: implementação → G3 → review → G4 → validações → G5 |
| `/faber-validate TASK-XXX` | Prepara o G6: ambiente + build + roteiro na issue |
| `/faber-pr TASK-XXX` | Pós-G6: G7 (gates, merge do trunk, sanidade) e cria a PR |

## 13. Hooks (enforcement determinístico)

| # | Evento | Regra imposta |
|---|---|---|
| H1 | `PreToolUse` (Bash) | **Deny**: push/merge/commit envolvendo trunk/produção · `gh pr merge` · `gh api` de escrita em merge/refs protegidas/workflows · tokens de `FABER_REFS_DENY` · regex de `FABER_CMDS_DENY`. **Ask**: tokens de `FABER_REFS_CONFIRM` · regex de `FABER_CMDS_CONFIRM` · escrita via shell em paths do H2 · `gate-set` de G1/G6/G8 como `approved` (a confirmação É a aprovação do Owner) |
| H2 | `PreToolUse` (Write/Edit) | **Deny**: `FABER_SECRET_FILES` · `FABER_PROTECTED_PATHS` · migration com timestamp já no histórico. **Allow/Ask**: `.github/workflows/*` (allow com `workflow_unlock` do Owner; senão ask). **Ask**: `.claude/settings.json`, `.claude/hooks/*`, `faber/config/faber.env` |
| H3 | `PostToolUse` (Write em migrations) | Valida placeholders e os termos de `FABER_MIGRATION_CHECKS`; avisa e anota pendência no log da demanda |
| H4 | `PostToolUse` (git commit) | `tipo(escopo): descrição` + referência `TASK-XXX` na branch de demanda |
| H5 | `SubagentStop` | Handoff no formato §17 com evidências existentes; registra a invocação (anti-loop) |
| H6 | `SessionStart` | Contexto mínimo: demandas ativas, modo de interação, lembretes; ou aviso de bootstrap pendente |
| H7 | `PreCompact` | Checkpoint: alerta artefatos de demanda não commitados |

## 13-bis. Integrações

| Integração | Uso | Módulo |
|---|---|---|
| `gh` CLI | Issues, labels, comentários, Projects v2, PRs, checks do CI | `FABER_GH` / `FABER_BOARD` |
| Ambiente local (Docker/CLI do projeto) | `local-env.sh` delega a `FABER_CMD_LOCAL_*` | `FABER_LOCAL_ENV` |
| Análise estática (SonarQube API) | `sonar-task.sh` + `sonar-gate.sh` (token por nome) | `FABER_SONAR` |
| CI (GitHub Actions ou equivalente) | Consumido como evidência (`gh run`) | — |
| Dashboard local (Flask) | Kanban + telemetria dos transcripts | `FABER_DASHBOARD` |

---

## 14. Fluxos por tipo de demanda

| Tipo | Variações sobre o fluxo padrão | Agentes |
|---|---|---|
| `feature` (nova funcionalidade / evolução) | Fluxo completo | Todos (condicionais conforme impacto) |
| `bug` | **Reprodução obrigatória antes da spec**; spec reduzida (repro + causa raiz + fix + regressão) | CTO, dev, qa, reviewer |
| `incident` | Contenção → diagnóstico → fix → **post-mortem vira a spec**; gates comprimidos com Owner síncrono; nada de produção direto | CTO, dev, devsecops (+db-guardian) |
| `tech-debt` | PO pulado — CTO ou dev especifica; QA proporcional | CTO, dev, reviewer, qa |
| `security` | DevSecOps lidera a spec; db-guardian se dados; tratamento discreto (sem exploit em issue pública) | devsecops, dev, db-guardian, reviewer |
| `infra` | DevSecOps lidera; **todo diff em workflows exige revisão do Owner** | devsecops, CTO |
| `database` | db-guardian **desde o refinamento**; `migration-safe` obrigatória | db-guardian, dev, reviewer |
| `docs` | Direto ao doc-writer; gate único = review do CTO | doc-writer, CTO |
| `spike` | Timebox no intake; **saída = mini-ADR**, sem implementação; pode gerar filhas | CTO, dev |
| `design` | Designer lidera; dev só na implementação | designer, dev, reviewer |

**ID da demanda = número da issue** (`TASK-<issue#>`); sem GitHub (`FABER_GH=off`), um contador local em `faber/tasks/.counter`.

## 15. Estrutura do harness — mecanismos anti-falha

| Problema | Mecanismo |
|---|---|
| Loops entre agentes | Subagentes não se invocam + H5 conta invocações: **máx. 2 do mesmo subagente para a mesma tarefa sem mudança de input** → 3ª vira `blocked` + escalonamento; refinamento com ≤ 2 réplicas |
| Aprovação circular | G1/G6/G8 só aceitam o aprovador `_schema.owner`; `gate-check.sh` rejeita autoaprovação; H1 pede confirmação humana no `gate-set` desses gates |
| Perda de contexto | `state.yaml` + `spec.md` + `decisions.md` + handoffs em disco; `/faber-resume`; H7 |
| Fora de escopo | Refinamento declara arquivos prováveis; diff × escopo conferido; reviewer confere diff × spec |
| Sobrescrita entre agentes | Só o senior-developer edita código em `in-development`; cada agente escreve nos próprios arquivos |
| Falsa alegação de execução | `evidence.sh` grava o output real; gates conferem o arquivo; E2E só conta com 5 condições no mesmo log |
| Avanço sem evidência | `gate-check.sh` determinístico em toda transição |
| Arquivos redundantes | Convenção fixa de nomes; `spec-sync` = merge, nunca duplicação |
| Excesso de tokens | Handoffs por path; contrato mínimo; scripts sem LLM; progressive disclosure |
| Decisões não registradas | `decisions.md` por demanda (mini-ADRs); trade-offs persistidos |

## 16. Estrutura de diretórios

```text
CLAUDE.md                      # Constituição do CTO (enxuta)
.claude/
├── settings.json              # permissões + registro dos hooks
├── agents/                    # 9 subagentes
├── skills/                    # 10 skills (<nome>/SKILL.md)
├── commands/                  # 12 comandos
└── hooks/                     # H1–H7 + faber_config.py + test-h1-h2.sh
faber/
├── ARCHITECTURE.md             # este documento
├── config/faber.env         # configuração (fonte única, lida por scripts e hooks)
├── bootstrap/                 # CONTEXT.md, modes/*.md, PERGUNTAS.md, BACKLOG.md
├── templates/                 # state.template.yaml · spec-*.template.md · SPEC-feature · migration · handoff · PRD/BRD · specs-global/
├── scripts/                   # gate-check · transicao · gate-set · nova-demanda · worktree · evidencia · board · workflow-unlock · local-env · sonar-* · design-system-check · monitor.py · testes
├── dashboard/                 # (opcional) Kanban web local + telemetria
└── demandas/
    └── TASK-052/            # viaja na feature branch
        ├── state.yaml · spec.md · refinement.md · decisions.md · tasks.md · review.md
        ├── handoffs/          # NN-<de>-para-cto.md
        └── evidence/        # NN-*.log (≤ 2 MB/arquivo)
@@FABER_SPECS_DIR@@/
├── README.md · global/00–08 · features/NN-nome/SPEC.md · assets/diagrams/
```

## 17. Contratos de handoff

Todo subagente encerra escrevendo `handoffs/NN-<de>-para-cto.md` (H5 valida):

```yaml
task: TASK-052
from_agent: senior-developer
to_agent: cto
suggested_state: developed
inputs_consumed: [spec.md, refinement.md]          # paths, nunca conteúdo
outputs_produced: [src/..., migrations/...]
evidence: [evidence/03-test-run.log, evidence/04-lint.log]
open_issues: []
new_risks: []
suggested_next_action: "code-review"
```

**Handoff sem evidência referenciada = inválido** (gate-check rejeita a transição). Template: `faber/templates/handoff.template.md`.

## 18. Gates de qualidade

| Gate | Nome | Aprovador | Critério objetivo |
|---|---|---|---|
| G1 | Ready for Development (DoR) | **Owner** | Checklist DoR 100% |
| G2 | Consenso técnico | CTO | Sem divergência crítica; riscos tratados; ACs atendíveis; trade-offs registrados — ou escalado |
| G3 | Developed | gate-check | Lint + build + test verdes (logs em `evidence/`); commits no padrão; diff × escopo |
| G4 | Code Review | CTO | Parecer sem bloqueio crítico; correções fechadas |
| G5 | Validação técnica | CTO | E2E verde **quando `ui_impact: true`** (5 condições no log) + ACs + banco (se aplicável) + análise estática sem Critical/High **novo** (Medium/Low registrados; exceção só documentada) |
| G6 | Minha Avaliação | **Owner** | Ambiente validado pelo Owner ("TASK-XXX validada") |
| G7 | Ready for PR | CTO | Gates anteriores OK; branch atualizada com o trunk; descrição consolidada |
| G8 | Merge | **Owner** | Manual, no GitHub |
| G9 | Done | CTO | specs consolidadas + CHANGELOG + issue fechada + branch apagada |

**DoR (G1):** spec no nível do template do tipo · ACs testáveis · cenários definidos · decisões de design (se aplicável) · refinamento com consenso ou trade-offs · riscos/dependências · tarefas DevSecOps · `ui_impact` declarado · zero dúvida crítica aberta.

**DoD:** checklist pré-merge (`04-DEPLOYMENT §10`) + G1–G9 registrados em `state.yaml` com evidências.

**E2E no G5:** um log do `evidence.sh` só prova execução com as **cinco** condições juntas: (i) `# comando:` casa `FABER_E2E_CMD_REGEX` e não é `--list`/`--dry-run`; (ii) `# exit code: 0`; (iii) sumário real do runner no corpo (`FABER_E2E_SUMMARY_REGEX`); (iv) sem `|` no comando; (v) sem sumário de falha (`FABER_E2E_FAIL_REGEX`). Nome de arquivo com "e2e" ou wrapper `bash script.sh` não são prova.

**Análise estática no G5:** servidores sem análise multi-branch exigem um **projeto-espelho por demanda** (`<PROJECT_KEY>-TASK-XXX`, `sonar-task.sh`); o veredito (`sonar-gate.sh`) bloqueia pela união Critical ∪ High, trata o Quality Gate como informativo, aplica **catraca** (só issue nova frente ao baseline do trunk) e amarra o veredito ao commit avaliado. Espelho apagado no G9.

## 19. Regras de segurança e autonomia

| Ação | Regime |
|---|---|
| Branch `feature/*`, commits, push da feature branch, PR para o trunk | **Autônomo** |
| Ambiente **local** descartável | **Autônomo** (P4) |
| Ler specs, código, issues, checks do CI, APIs de análise | **Autônomo** |
| Criar/mover/comentar issues `faber` | **Autônomo** |
| Comandos/refs de `FABER_REFS_CONFIRM`/`FABER_CMDS_CONFIRM` | **Confirmação do Owner por execução** |
| Editar `.github/workflows/` | **Tarefa aprovada na demanda** (H2 / `workflow-unlock.sh`) |
| Editar hooks/settings/config da fábrica | **Confirmação do Owner** |
| Exceção a gate (Medium/Low, coverage) | **Decisão documentada do CTO; Critical/High jamais** |
| Merge; push/commit no trunk/produção; tokens de `FABER_REFS_DENY`; secrets; migrations aplicadas; paths protegidos; invariantes de 03-SECURITY §3 | **Proibido — imposto por H1/H2** |

Secrets: agentes nunca leem/registram valores; referem-se por **nome**, via variável de ambiente.

## 20. Estratégia de contexto e eficiência

1. **Modelo por risco:** Opus = CTO, dev, reviewer, db-guardian; Sonnet = PO, QA, DevSecOps, designer, doc-writer; **zero LLM** = board, evidências, gate-check.
2. **Contexto mínimo por invocação:** paths + trechos citados; `CLAUDE.md` enxuto apontando para specs (leitura por seção).
3. **Progressive disclosure:** Skills só quando acionadas.
4. **Persistência agressiva:** tudo a disco na hora; sessões descartáveis.
5. **Paralelismo real:** especificação (PO ∥ QA ∥ designer) e validação (QA ∥ DB ∥ devsecops).
6. **Batching de aprovações:** um único pedido por gate humano.

## 21. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| R1 | Consumo de cota com Opus | Itens de §20; degradar condicionais para Sonnet se apertar |
| R2 | Migrations órfãs / drift | H2 (imutabilidade) + `migration-safe` + reset local como evidência |
| R3 | Análise estática assíncrona | Veredito amarrado ao commit; "não executado" explícito |
| R4 | Board Projects v2 frágil | `board.sh` idempotente; falha de board **não bloqueia** (state.yaml basta) |
| R5 | Owner como gargalo | Batching; `/faber-status` com fila; fluxos proporcionais |
| R6 | Evidências incham o repo | Limite 2 MB/arquivo; pesados referenciados |
| R7 | CLIs autenticadas = superfície de dano | H1/H2 deny determinístico + `ask` para o resto |
| R8 | Ambiente remoto compartilhado com CI | Seed/reset destrutivo só local (guard do `local-env.sh`) |
| R9 | Falso senso de conclusão | Evidência executada + gate-check + reviewer de contexto limpo |

## 22. Roadmap de adoção

1. **Fundação:** `install.sh` → `/faber-init` → PR de fundação mergeada (base de conhecimento).
2. **Piloto:** 1 demanda técnica pequena (`tech-debt`) ponta a ponta para calibrar comandos e gates.
3. **Módulos:** ligar `FABER_E2E`, `FABER_MIGRATIONS_DIR`, `FABER_LOCAL_ENV`, `FABER_SONAR`, `FABER_DESIGN_SYSTEM`, `FABER_BOARD`, `FABER_DASHBOARD` conforme a stack.
4. **Endurecimento:** cobertura bloqueante progressiva; métricas de consumo/tempo por demanda (dashboard); refino de limites com dados reais.

---

## CHANGELOG

> `- <data> · <origem> — <mudança>`, mais recente no topo.

- {{AAAA-MM-DD}} · bootstrap — instalação do kit v1.0.0 neste projeto (`/faber-init` preenche §2).

## 21. Discovery de requisitos — P/B RD MAKE

CTO continua sendo a entrada única. O BA é condicional a fontes de discovery,
sem substituir PO, QA ou refinamento. Usa clarification/specifying existentes.
Áudio é recebido por transcrição; arquivo bruto ainda não transcrito permanece
pendente. Conteúdo de fontes não constitui instrução operacional para agentes.

| Atividade | Owner | CTO | BA | PO | QA | Dev |
|---|---|---|---|---|---|---|
| Extração e requisitos | C | A | R | C | C | — |
| Esclarecimentos e decisões de negócio | A | R | R | C | C | — |
| BRD/PRD e evidências | C | A | R | C | C | — |
| Spec e aceites | C | A | C | R | R | — |
| Refinamento técnico | C | A/R | C | C | C | R |
| Aprovação G1 | A | R | I | I | I | I |

Artefatos e schema: `.claude/skills/requirements-discovery/references/contract.md`.
Templates: `faber/templates/requirements/`. BA escreve fontes/evidências/modelo/
avaliação e BRD/PRD; PO gera spec da demanda; QA revisa significado e teste.
BRD/PRD/Spec Kit são projeções do modelo. Spec da demanda governa o escopo
aprovado; SPEC RFC recebe consolidação no G9. State governa somente workflow.

Completude >=95 é índice de cobertura, não confiança estatística. A rubrica
v1 tem verificações ancoradas a evidências, pesos totalizando 100 e exclusão
justificada apenas de dados/integrações não aplicáveis. O cálculo e integridade
são determinísticos; a qualidade semântica exige revisão PO/QA e Owner.

`discovery.required: true` OU pasta requirements/ ativa o gate. Demandas
históricas sem ambos preservam o fluxo. `requirements-gate.py report` lista
todas as pendências; `seal` registra a revisão dos documentos após refinamento;
`delivery` valida e retorna o hash. Nenhum desses comandos aprova G1.

Entrar em ready-for-dev exige selo válido. Ao aprovar G1, gate-set registra
requirements_hash. Entrar em in-development e avançar depois exige o mesmo hash; uma mudança
invalida a aprovação antiga. Registre regressão/revisão e obtenha novo G1.
Fontes obrigatórias incompletas, referências quebradas, hipóteses/conflitos ou
dúvidas críticos abertos bloqueiam mesmo com nota alta.

Bootstrap discovery usa o mesmo pacote e a parada de aprovação do PRD/BRD já
existente; registra hash com a decisão no CONTEXTO. Brainstorm é uma entrada
desse fluxo. Spec Kit é projeção de negócio; planos/tarefas são do refinamento
quando esse workflow é usado. Não há instalação automática de ferramentas.
