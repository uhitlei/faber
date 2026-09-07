<div align="center">

# Faber

**Uma fábrica de software governada por gates, para o Claude Code.**

Nove subagentes especializados, doze comandos, dez skills e sete hooks
determinísticos que impõem as regras **por código, não por prompt**.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/testes-170%20casos-black.svg)](#verificação--evidência-não-promessa)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-black.svg)](https://code.claude.com/docs/en/plugins)

[Instalar](#instalação) · [Como funciona](#como-funciona) · [O que é instalado](#o-que-é-instalado) · [English](README.md)

</div>

---

*Faber* é o latim para **quem faz** — a raiz de *fabricar* e de *fábrica*.

Cada demanda nasce como `TASK-<issue#>`, roda em worktree próprio e passa por
nove gates. Três são seus: **G1** ready-for-dev, **G6** sua avaliação, **G8**
merge. Cada gate exige **evidência executada** — um comando real, a saída real
dele, gravada em disco.

O orquestrador (o CTO) roda na sua sessão principal. Os especialistas rodam
como subagentes com contexto limpo. Tudo que importa vai a disco e é commitado
na branch da demanda, então `/faber-resume TASK-42` reconstrói qualquer sessão
do zero. Sessões são descartáveis; o repositório é a memória.

## Instalação

```
/plugin marketplace add uhitlei/faber
/plugin install faber@faber
```

depois, dentro do repositório onde você quer a fábrica:

```
/faber:install
```

<details>
<summary>Outras duas portas de entrada</summary>

**Peça para a IA.** Em qualquer sessão do Claude Code, no seu repositório:

> Instale o Faber neste repositório seguindo
> `https://github.com/uhitlei/faber/blob/main/INSTALL.pt-BR.md`

**Uma linha de shell.**

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh | bash
```

Procedimento completo, flags e diagnóstico: **[INSTALL.pt-BR.md](INSTALL.pt-BR.md)**.

</details>

O plugin entrega três comandos — `/faber:install`, `/faber:update`,
`/faber:doctor` — e nada mais. A fábrica em si é escrita dentro do **seu**
repositório, renderizada com o seu aprovador, as suas branches e os seus
comandos de validação. Nada nela funciona antes disso, de propósito: uma
fábrica meio instalada aprovaria gates contra a configuração de outra pessoa.

### Pré-requisitos

- **Claude Code** autenticado.
- `git`, `bash ≥ 3.2`, `python3` com **PyYAML** (`pip3 install pyyaml`).
- `gh` CLI, se quiser que o ID da demanda seja o número da issue no GitHub
  (recomendado). Sem ele, um contador local assume.
- Módulos opcionais, cada um ligado em `faber/config/faber.env`: SonarQube,
  Playwright/Cypress, subida de ambiente local, dashboard Kanban em Flask.

## O instalador lê o seu repositório primeiro

Nenhum modelo participa da detecção. Ele conta arquivos de código, lê
manifestos e procura sinais conhecidos, e então escolhe o modo de bootstrap:

| Seu repositório | Modo | O que o `/faber-init` produz |
|---|---|---|
| tem código e histórico | `existing-repo` | specs globais lidas do código, inventário de features e a configuração real (lint/build/test, migrations, paths protegidos) |
| specs em **Spec Kit** | `spec-kit` | constituição → regras; cada `spec.md` → SPEC RFC de 17 seções; `plan.md` → arquitetura; `tasks.md` → backlog |
| um **PRD/BRD** | `prd` | arquitetura `[PROPOSTA]`, specs de feature derivadas dos requisitos, backlog priorizado |
| um **brainstorm** | `brainstorm` | PRD + BRD seguindo o **seu** guia, para para aprovação, segue como `prd` |
| transcrições e notas de reunião | `discovery` | o business analyst extrai evidências e requisitos, gera BRD/PRD e resolve lacunas |
| nada ainda | `empty` | pergunta qual insumo você vai trazer |

E faz a única pergunta que ele se recusa a responder por você: você quer ser
chamado **só nos gates de validação** ou **passo a passo**?

## Como funciona

```text
/faber-task → spec (PO ∥ QA ∥ designer) → refinamento duplo (CTO × dev) → [G1 · você]
→ /faber-develop: implementação → G3 (lint/build/test com evidência) → review de contexto limpo → G4
→ validações paralelas (QA ∥ db-guardian ∥ devsecops) → G5 → /faber-validate → [G6 · você]
→ /faber-pr → G7 → PR → [G8 · você, no GitHub] → doc-writer consolida specs → G9 · done
```

Os hooks são o que torna isso real em vez de aspiracional. Eles bloqueiam push
e merge no trunk e em produção, edição de secrets, migrations já aplicadas e
arquivos protegidos; exigem um diálogo de confirmação humana para aprovar um
gate humano; e conferem que todo handoff carrega evidência que existe de fato
e não está vazia.

## O que é instalado

```text
CLAUDE.md              # a constituição do CTO (um CLAUDE.md anterior vira a seção 9)
.claude/
  settings.json        # permissões + hooks (mesclado, não sobrescrito)
  agents/   (9)        # business-analyst · product-owner · senior-developer · code-reviewer
                       # qa · devsecops · doc-writer · db-guardian · product-designer
  skills/   (10)       # requirements-discovery · requirements-readiness · spec-task · evidence
                       # spec-sync · migration-safe · local-env · e2e-runner · sonar-gate · design-system-check
  commands/ (12)       # /faber-init /faber-task /faber-bug /faber-spike /faber-incident /faber-discovery
                       # /faber-status /faber-resume /faber-approve /faber-develop /faber-validate /faber-pr
  hooks/    (H1–H7)    # guarda-vidas parametrizados por faber/config/faber.env
faber/
  ARCHITECTURE.md       # a arquitetura (numeração estável — agentes citam §N)
  config/faber.env     # owner, branches, comandos, módulos, refs protegidos
  bootstrap/           # CONTEXT.md (modo detectado) + playbooks dos seis modos
  scripts/             # gate-check · transition · gate-set · new-task · worktree · evidence · board
  templates/           # state.yaml · specs por tipo · SPEC RFC · migration · handoff · PRD/BRD · globais
  tasks/               # uma pasta por TASK-XXX, viajando na branch da demanda
<specs>/               # base canônica: README + global/00–08 + features/
```

## Verificação — evidência, não promessa

As regras da fábrica são testadas. Depois de instalar, no seu repositório:

```bash
bash .claude/hooks/test-h1-h2.sh           # 46 casos: o que os hooks negam, confirmam e liberam
bash faber/scripts/test-gate-check.sh      # 43 casos: transições bloqueadas e liberadas
bash faber/scripts/test-sonar-gate.sh      # 20 casos (módulo Sonar, com curl stubado)
python3 faber/scripts/test-monitor.py      # 40 casos (monitor de estado)
python3 faber/scripts/test-requirements.py # 21 casos (readiness de requisitos)
```

170 casos. Todos criam sandboxes descartáveis e nunca tocam no seu
repositório. O `/faber:doctor` roda essas suítes por você e reporta o que falta.

## Idioma

O Faber é bilíngue. O instalador pergunta em que idioma os agentes devem
trabalhar, ou você passa `--lang pt-BR` / `--lang en`:

| Camada | Idioma |
|---|---|
| Prosa dos agentes, skills e comandos · `CLAUDE.md` · `faber/ARCHITECTURE.md` · os templates | **o pacote que você escolheu** — `kit/lang/pt-BR` ou `kit/lang/en`, os dois completos |
| Nomes de comando, pastas, chaves `FABER_*`, `state.yaml`, colunas do board, labels do GitHub | **inglês nos dois pacotes** |
| O que a fábrica **escreve** — specs, issues, handoffs, mensagens de gate | segue `FABER_LANG` (vem do `--lang`, mutável depois) |
| Scripts e hooks | neutros de idioma |

O contrato de máquina é idêntico nos dois idiomas de propósito. Um `state.yaml`
por idioma faria os scripts, o board e o dashboard falarem dois dialetos do
mesmo dado — então uma instalação em português continua gravando
`state: my-review`, e o time em português lê prompts em português.

## Documentação

- **[INSTALL.pt-BR.md](INSTALL.pt-BR.md)** — instalação, flags, verificação, diagnóstico.
- [docs/pt-BR/MODOS-DE-BOOTSTRAP.md](docs/pt-BR/MODOS-DE-BOOTSTRAP.md) — os seis modos e o que cada um gera.
- [docs/pt-BR/PERSONALIZACAO.md](docs/pt-BR/PERSONALIZACAO.md) — cada chave do `faber.env` e os módulos opcionais.
- [docs/pt-BR/REQUISITOS-DISCOVERY.md](docs/pt-BR/REQUISITOS-DISCOVERY.md) — o business analyst e o gate de readiness.
- `plugins/faber/kit/faber/ARCHITECTURE.md` — a arquitetura completa.

## Contribuindo

Issues e pull requests são bem-vindos — veja [CONTRIBUTING.md](CONTRIBUTING.md).
A regra dura: **mudança em guarda-vidas ou em gate vem com um caso de teste que
falha sem ela.**

## Licença

MIT — veja [LICENSE](LICENSE).
