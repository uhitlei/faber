# Plano: Faber em Windows, Linux e macOS — e em Claude Code, Cursor e Codex

Escrito em 2026-10-28 a partir de três levantamentos: o código do kit (v2.0.0,
branch `main`), a documentação oficial de cada ferramenta e os fóruns de suporte.
Cada afirmação sobre ferramenta externa traz uma marca:

- **[V]** verificado na documentação oficial em outubro de 2026;
- **[F]** relatado em fórum/issue (comportamento real, pode mudar sem aviso);
- **[I]** inferido — precisa de confirmação num spike antes de virar código.

O plano é dividido em cinco fases. Nenhuma fase começa antes de a anterior
passar no CI, e as decisões que só o Owner pode tomar estão reunidas na §9.

---

## 1. Diagnóstico: onde o Faber está hoje

### 1.1 Plataformas

A premissa "só atende macOS" está parcialmente errada, e vale corrigi-la antes
de planejar:

| Plataforma | Estado real | Evidência |
|---|---|---|
| macOS | suportado | alvo primário; bash 3.2 é a baseline de `CONTRIBUTING.md` |
| Linux | **já funciona e é testado** | `ci.yml` roda as seis suítes e o install end-to-end em `ubuntu-latest`; `package.json` declara `os: [darwin, linux]` |
| Windows (WSL2) | funciona sem ser testado | é Linux; `bin/faber.js` manda o usuário para lá |
| Windows nativo | **não funciona** | `bin/faber.js` encerra com erro em `win32`; tudo é bash + python3 |

Logo, a demanda real é **Windows nativo**, mais a formalização do Linux (CI já
existe, falta documentação e um teste em pelo menos uma distro além do Ubuntu).

### 1.2 Anatomia do kit (o que precisa ser portado)

| Camada | Tamanho | Linguagem | Observação |
|---|---|---|---|
| Hooks H1–H7 | 7 arquivos, ~800 linhas | bash envolvendo Python (heredoc) | a lógica já é Python; o bash só lê o stdin e chama `python3` |
| Scripts `faber/scripts/*.sh` | 23 arquivos, ~3.700 linhas | bash, 13 deles com Python embutido | `gate-check`, `transition`, `evidence`, `new-task`, `worktree`, `board`, `sonar-*`… |
| Scripts `.py` | ~1.500 linhas | Python | `monitor.py`, `requirements.py`, `faber_config.py` |
| Dashboard | ~2.000 linhas | Python/Flask | opcional; `dashboard.sh` assume `.venv/bin/python` |
| Instalador | `install.sh` 490 linhas + `bootstrap.sh` + `bin/faber.js` | bash | render de `@@FABER_*@@`, merge de `settings.json`, git |
| Prosa | agentes (9), comandos (12), skills (10), CLAUDE.md, ARCHITECTURE, templates | Markdown, en + pt-BR | contrato de máquina em inglês nos dois idiomas |

### 1.3 Pontos que quebram no Windows nativo (auditoria do código)

Em ordem de gravidade. Os quatro primeiros são **falhas silenciosas de
segurança**: o guarda-vidas não bloqueia e ninguém percebe.

1. **H1 não dispara sem Git Bash.** No Windows sem Git Bash, o Claude Code não
   registra a ferramenta `Bash` e usa a ferramenta `PowerShell` [V]. O matcher
   `"Bash"` em `settings.json` nunca casa → `git push origin main` passa livre.
2. **H2/H3 comparam caminhos com `/`.** No Windows o `file_path` chega com `\`
   mesmo sob Git Bash [V]. `rel.startswith(".github/workflows/")`,
   `"/" + p in path`, `re.match(mig + r"/(\d{8,14})_…")` falham → edição de
   workflow, de secret e de migration aplicada **deixa de ser negada**.
3. **Raiz do git vs. cwd com separadores misturados.** `git rev-parse
   --show-toplevel` devolve `C:/x/y`; o `cwd` do hook chega `C:\x\y`.
   `os.path.relpath` entre os dois produz lixo → mesmas consequências do item 2.
4. **`python3` não existe no PATH do Windows** (o instalador oficial cria
   `py.exe` e, opcionalmente, `python.exe`). Todos os 23 scripts e 7 hooks
   chamam `python3`; o hook falha, e falha de hook em PreToolUse não é deny.
5. **Encoding.** 46 chamadas `open()` sem `encoding=`; o Windows abre em
   cp1252 → `UnicodeDecodeError` ao ler qualquer arquivo do kit (acentos,
   "🏭"). O `print("🏭 …")` em console cp1252 lança `UnicodeEncodeError`.
   Fóruns do Cursor relatam BOM UTF-8 no stdin dos hooks no Windows [F].
6. **CRLF.** Não há `.gitattributes`. Clone com `core.autocrlf=true` converte
   `.sh` para CRLF → bash falha com `\r: command not found`.
7. **Bit de execução.** `settings.json` invoca `"$CLAUDE_PROJECT_DIR"/.claude/hooks/h1-bash-guard.sh`
   diretamente; NTFS não tem `chmod +x`. Sob Git Bash costuma funcionar pelo
   shebang, mas é heurística — invocar via interpretador é o único caminho
   garantido.
8. **`.venv/bin/python`** no `dashboard.sh`: no Windows é `.venv\Scripts\python.exe`.
9. **`bash -c "$CMD"`** em `evidence.sh`/`local-env.sh`: os comandos de
   validação do usuário (`npm run lint`) precisam de um shell; no Windows nativo
   é `cmd.exe` ou PowerShell. `make lint` (default sem manifesto) não existe lá.
10. **Caminhos longos.** `.claude/worktrees/TASK-NNN/faber/tasks/TASK-NNN/handoffs/…`
    pode passar de 260 caracteres sem `core.longpaths=true`.
11. **Symlinks** em `test-sonar-gate.sh` (`ln -sf`) exigem modo desenvolvedor no
    Windows — só nos testes, mas o CI do Windows vai quebrar.
12. **`bootstrap.sh`** usa `curl | tar`, `/dev/tty` e `mktemp -d`: existe sob
    Git Bash, não em PowerShell. Precisa de um `bootstrap.ps1`.
13. `bin/faber.js` recusa `win32` explicitamente.

O que **não** é problema: `sed -E`, `mktemp`, `date +%z`, `stat -f/-c` (já tem
fallback), `timeout/gtimeout` (já tem fallback) — tudo existe no Git Bash.

### 1.4 Pontos acoplados ao Claude Code

| Mecanismo | Onde | Cursor | Codex |
|---|---|---|---|
| `CLAUDE.md` como constituição | raiz | lê (CLI [V]; IDE com toggle "third-party" [F]) | não lê; lê `AGENTS.md` [V] |
| `.claude/commands/*.md` + `$ARGUMENTS` | 12 comandos | sem página de docs; `.cursor/commands` [F]; sem `$ARGUMENTS` [I]; Cursor empurra para skills (`/migrate-to-skills`) [V] | prompts customizados **deprecados** e só em `~/.codex/prompts` (nível usuário) [V] |
| `.claude/agents/*.md` com `tools:` e `model:` | 9 agentes | lê `.claude/agents` nativamente [V]; **ignora `tools:`** (só há `readonly`) [V]; ids de modelo diferentes | `.codex/agents/*.toml` (`developer_instructions`, `model`) [V]; sem restrição de ferramenta; subagente herda sandbox do pai [V] |
| `.claude/skills/*/SKILL.md` | 10 skills | lê `.claude/skills` e `.agents/skills` [V] | lê `.agents/skills` [V] e `.codex/skills` [S: só no código-fonte] |
| Hooks em `.claude/settings.json` | H1–H7 | importa hooks do Claude com mapeamento [V]; **`ask` não é aplicado** ("aceito pelo schema, não enforced") [V]; PostToolUse não bloqueia [V] | `hooks.json` compatível com o Claude [V]; **`ask` não suportado — o hook falha e a ferramenta roda** [S]; projeto precisa de trust + trust por hash via `/hooks` [V] |
| `permission_mode` no input do hook (modo bypass) | H1/H2 | **não existe** [V] | existe [V] |
| Plugin `.claude-plugin/marketplace.json` | distribuição | formato próprio `.cursor-plugin/plugin.json` [V] | **aceita manifests Claude-compatíveis** e lê `.claude-plugin/marketplace.json` [V]; só skills/hooks/MCP; a extensão IDE não suporta plugins [V] |
| Subagentes em paralelo (G5) | comandos | sim (`/name`, automático) [V] | sim (`agents.enabled` default on) [V] |

Três conclusões estruturais saem dessa tabela e orientam todo o plano:

- **O "ask" não é um contrato portátil.** Hoje o diálogo de confirmação É a
  decisão do Owner nos gates G1/G6/G8 (H1 regra 8) e no `workflow-unlock`
  (regra 9). Em Cursor e Codex isso vira passagem livre. A prova de humano
  precisa sair do diálogo e ir para um artefato em disco (§4.3).
- **Comandos viram skills.** É a única superfície invocável por `/` que as três
  ferramentas leem, e as três aceitam o padrão Agent Skills.
- **`AGENTS.md` vira a constituição.** `CLAUDE.md` passa a ser um ponteiro.

---

## 2. Princípios de arquitetura da v3

1. **Uma fonte, N adaptadores.** O kit continua tendo um só contrato de máquina
   (`faber/`, `state.yaml`, gates, evidências). O que muda por ferramenta é
   gerado por um comando (`faber adapt`) a partir dessa fonte — nunca editado
   à mão em dois lugares.
2. **Lógica em Python, lançadores finos.** A regra de negócio dos hooks e dos
   scripts sai do bash e vai para módulos Python testáveis. O bash sobrevive só
   como lançador de 2 linhas (e um `.cmd` equivalente no Windows).
3. **Caminhos sempre normalizados.** Toda comparação de caminho passa por uma
   única função (`faber_paths.rel_posix(path, root)`) que resolve
   `realpath`, `normcase` e converte para `/`. Nenhum hook compara string
   crua de novo.
4. **Falhar fechado onde é guarda-vidas.** Hook que não consegue parsear o
   input ou localizar a config **nega** (hoje faz `sys.exit(0)` = sem
   opinião). Em Cursor, `failClosed: true` em todo hook de permissão.
5. **Prova humana por artefato, não por diálogo** (§4.3).
6. **Compatibilidade declarada, não prometida.** Uma matriz de suporte (§7)
   diz exatamente o que cada ferramenta/OS garante e o que degrada.

### 2.1 Por que Python e não Node para o motor

| Critério | Python | Node |
|---|---|---|
| Já é requisito do Faber | sim (PyYAML, monitor, dashboard) | não — o Claude Code nativo não exige Node |
| Volume já escrito | ~1.500 linhas + toda a lógica dos hooks | 51 linhas (`faber.js`) |
| Garantido no Cursor/Codex | não (nenhum dos dois expõe runtime) | não |
| Resolução no Windows | `py -3` sempre instalado pelo instalador oficial; `python` opcional | `node` só se instalado |

Nenhum dos dois é universal; o Python já é a dependência declarada e evita
reescrever o que existe. **Decisão recomendada: Python 3.9+**, com um
resolvedor de interpretador nos lançadores (`python3` → `python` → `py -3`).

### 2.2 Como os hooks são invocados em cada ferramenta/OS

Este é o ponto mais delicado do plano, porque `settings.json`/`hooks.json` são
**commitados** e lidos por máquinas com sistemas diferentes.

| Ferramenta | Como executa o `command` | Forma escolhida |
|---|---|---|
| Claude Code (mac/Linux) | `sh -c` [V] | `bash "$CLAUDE_PROJECT_DIR/faber/bin/faber-hook" h1` |
| Claude Code (Windows + Git Bash) | Git Bash [V] | o mesmo — Git Bash vem com o Git for Windows, que já é requisito |
| Claude Code (Windows sem Git Bash) | PowerShell [V]; não há ferramenta Bash, só PowerShell | **não suportado para a fábrica** (ver §9-D1); `faber doctor` detecta e explica |
| Codex (POSIX) | `/bin/sh` [V] | `"command": "faber/bin/faber-hook h1"` |
| Codex (Windows) | `%COMSPEC%` (cmd.exe) salvo `commandWindows` [V] | `"commandWindows": "faber\\bin\\faber-hook.cmd h1"` |
| Cursor (POSIX) | não documentado; funciona como shell | `faber/bin/faber-hook h1` |
| Cursor (Windows) | não documentado; fóruns relatam PowerShell, BOM, prefixo `cmd /c` [F] | **spike S2** decide entre `cmd /c faber\bin\faber-hook.cmd h1` e depender da importação nativa de `.claude/settings.json` |

`faber/bin/faber-hook` (POSIX sh) e `faber/bin/faber-hook.cmd` (Windows)
fazem a mesma coisa: resolvem o interpretador e executam
`faber/hooks/<nome>.py` repassando stdin. Em exec-form (Claude), `args` com
`${CLAUDE_PROJECT_DIR}` em barras normais funciona em todas as plataformas [V].

O matcher do H1 passa a ser `"Bash|PowerShell"` no Claude [V], `Shell` no
Cursor [V] e `Bash` no Codex [V] — gerado pelo adaptador.

---

## 3. Fase 0 — Spikes (antes de qualquer código de produção)

Cada spike é uma `TASK` da própria fábrica (dogfooding), com `evidence/` real.
Nenhuma decisão de design marcada **[I]** vira código antes do spike fechar.

| # | Pergunta | Como responder | Decisão que depende |
|---|---|---|---|
| S1 | O Claude Code lê `.agents/skills/`? Skills com `disable-model-invocation: true` aparecem como `/faber-task` e recebem argumentos anexados quando o `SKILL.md` não usa `$ARGUMENTS`? Frontmatter desconhecido (`readonly`) em `.claude/agents` gera erro ou é ignorado? | Repo mínimo; `claude --debug`; capturar o menu `/` | §4.1 (diretório único de skills), §4.2 |
| S2 | Cursor no **Windows**: qual shell executa `hooks.json`? `cmd /c …cmd` funciona? Há BOM no stdin? Com hooks em `.cursor/hooks.json` **e** em `.claude/settings.json`, o mesmo hook dispara duas vezes? Skill em `.agents/skills` e `.claude/skills` com o mesmo nome é carregada duas vezes? | Hook que grava `sys.argv`, `os.environ['COMSPEC']`, primeiros bytes do stdin em log; VM Windows 11 | §2.2, §4.1, §5 |
| S3 | Codex: formato exato do `tool_input.command` em `apply_patch` (para o H2 ler `*** Update File:`); fluxo de trust (`/hooks`, hash) na prática; `prefix_rule` com `decision="prompt"` realmente pergunta no CLI e no IDE?; `commandWindows` sob cmd.exe | Repo mínimo em mac e Windows | §4.3, §5.3 |
| S4 | Claude Code no Windows com Git Bash: formato de `CLAUDE_PROJECT_DIR` e de `cwd` (barras?); hook `.sh` sem bit x executa?; `permission_mode` chega? | Hook de log; VM Windows 11 | §2.2, lib de caminhos |
| S5 | Cursor: a importação nativa de `.claude/settings.json` honra `deny` em `preToolUse Write`? Qual a latência/timeout que faz o deny ser perdido [F]? | 20 execuções cronometradas | se o adaptador Cursor é obrigatório ou opcional |

Saída da fase: `docs/pt-BR/SPIKES-MULTIPLATAFORMA.md` com as respostas e os
logs; §9 do plano revisada com as decisões fechadas.

---

## 4. Fase 1 — Modelo multi-ferramenta (a fonte canônica)

### 4.1 Constituição e skills

- `AGENTS.md` passa a ser o arquivo que o instalador renderiza (o conteúdo é o
  `CLAUDE.md` de hoje). `CLAUDE.md` contém só `@AGENTS.md` — o Claude Code
  importa [V] e o Cursor evita a dupla injeção relatada em fórum [F].
- Limite: o Codex corta `AGENTS.md` em 32 KiB (`project_doc_max_bytes`) [V]. O
  `CLAUDE.md` atual tem 9,6 KB; a regra "CLAUDE.md anterior preservado como
  seção 9" pode estourar → o instalador passa a mover o legado para
  `faber/legacy-rules.md` e referenciá-lo, avisando quando o total passar de
  28 KiB.
- Os **12 comandos viram skills** `faber-task`, `faber-develop`, … com
  `disable-model-invocation: true` (só o humano invoca). Sem `$ARGUMENTS` no
  corpo: o Claude anexa os argumentos ao prompt quando o placeholder não
  existe [V]; Cursor e Codex passam o texto digitado junto. O texto da skill
  diz "a demanda é o que o Owner escreveu depois do comando".
- Diretório único de skills: `.agents/skills/` se S1 confirmar que o Claude lê;
  senão `.claude/skills/` + adaptador Codex apontando `[[skills.config]]`
  para ele (verificar em S3 se aceita caminho fora dos padrões). Nunca copiar
  para dois diretórios que o Cursor leia ao mesmo tempo — ele carrega os dois.
- As 10 skills existentes ficam onde estão; só o diretório muda.

### 4.2 Agentes

Fonte canônica continua `.claude/agents/*.md` (o Cursor lê nativamente [V]).
O adaptador gera:

- `.cursor/agents/<nome>.md` — mesmo corpo; frontmatter com `model` no id do
  Cursor e `readonly: true` para `code-reviewer`, `db-guardian`,
  `product-designer` (os que hoje não têm `Edit`). Como `.cursor/` vence
  `.claude/` para o mesmo nome [V], não há duplicata.
- `.codex/agents/<nome>.toml` — `name`, `description`,
  `developer_instructions` (= corpo), `model` mapeado, `features.shell_tool =
  false` onde o agente não tem Bash. Sem equivalente a `tools:`; a restrição
  vira instrução explícita no `developer_instructions` ("você não edita
  código") e é anotada na matriz de degradação.
- Mapa de modelos em `faber.env`: `FABER_MODEL_STRONG` / `FABER_MODEL_FAST`
  por ferramenta (`opus`/`sonnet` hoje → ids do Cursor e do Codex), para o
  Owner trocar sem editar nove arquivos.

### 4.3 Prova humana por ticket (substitui o diálogo "ask")

Hoje: H1 devolve `ask` quando o agente roda `gate-set TASK G1 approved`; o
clique do Owner no diálogo é a aprovação. Isso **não existe** no Cursor (ask
não aplicado [V]) nem no Codex (ask faz o hook falhar e a ferramenta roda [S]).

Novo mecanismo, igual nas três ferramentas:

1. O Owner, **no próprio terminal** (fora do agente), roda
   `faber approve TASK-42 G1` (ou `faber unlock-workflows TASK-42`).
2. O comando grava `faber/tasks/TASK-42/approvals/G1.yaml` com `by`, `at`,
   `state_sha256` (hash do `state.yaml` no momento) e `nonce`, e faz o commit
   `chore(faber): TASK-42 G1 approved by <owner>`.
3. `gate-set`/`transition` só aceitam `G1|G6|G8 approved` se existir ticket
   válido, não consumido, cujo `state_sha256` bate — e o consomem.
4. H1 (Claude), `beforeShellExecution` (Cursor) e `prefix_rule` (Codex)
   passam a **negar** o agente rodando `faber approve`, `faber
   unlock-workflows` e `gate-set … G1|G6|G8 … approved` sem ticket. Nenhum
   `ask` sobra nos caminhos críticos.
5. O comando `/faber-approve` deixa de registrar o gate: ele **pede** ao Owner
   que rode o `faber approve` no terminal, espera, verifica o ticket e segue.
6. No Claude Code o `ask` continua existindo como tripwire adicional (nada
   impede dois níveis). Em modo bypass o comportamento não muda — já era deny.

Honestidade sobre o limite: um hook não distingue o terminal do humano do
terminal do agente; o que ele faz é negar o comando quando vem **pelo agente**.
É o mesmo nível de garantia que o Codex declara para os próprios hooks ("um
guardrail útil, não um perímetro completo" [V]) — e é mais forte que o diálogo
de hoje, que no Cursor e no Codex não existe.

### 4.4 Os outros hooks por ferramenta

| Hook | Claude | Cursor (nativo) | Codex |
|---|---|---|---|
| H1 bash guard | PreToolUse `Bash\|PowerShell`, deny/ask | `beforeShellExecution` deny (ask → deny) | PreToolUse `Bash` deny + `.codex/rules/faber.rules` (`forbidden` para push/merge no trunk, `prompt` para FABER_REFS_CONFIRM — o único "ask" real do Codex [V]) |
| H2 write guard | PreToolUse `Write\|Edit\|…` | `preToolUse` matcher `Write` (cobre Edit) [V], `failClosed: true` | PreToolUse `Write\|Edit` → `tool_name` é `apply_patch`; o hook parseia o patch (`*** Update File:`/`*** Add File:`/`*** Delete File:`) e nega se **qualquer** arquivo do patch cair numa regra |
| H3 migration check | PostToolUse `decision: block` | `postToolUse` só tem `additional_context` [V] → vira aviso ao agente + pendência no `log.md` | PostToolUse `block` substitui o resultado [V] — equivalente |
| H4 commit msg | PostToolUse `Bash` block | `afterShellExecution` → aviso; **complemento**: `commit-msg` hook do git instalado por `faber adapt --git-hooks` (funciona em qualquer ferramenta) | idem Claude |
| H5 handoff check | SubagentStop block | `subagentStop` `followup_message` [V] (reinjeta a correção) | SubagentStop block [V] |
| H6 contexto | SessionStart stdout | `sessionStart` `additional_context` [V] | SessionStart stdout [V] |
| H7 checkpoint | PreCompact `systemMessage` | `preCompact` `user_message` (observacional) [V] | PreCompact [V] |

O H4 ganha o hook git nativo porque é o único que tem equivalente universal —
e a regra "`tipo(escopo): descrição` + `TASK-N` na branch de demanda" passa a
valer até para commits feitos à mão.

### 4.5 `faber.env` e config por ferramenta

Novas chaves (com default), todas lidas por `faber_config.py` e pelo motor:

```
FABER_TOOLS="claude"                 # claude,cursor,codex — para quem gerar adaptadores
FABER_SHELL=""                       # vazio = auto (sh · Git Bash · cmd); comandos FABER_CMD_* rodam aqui
FABER_PYTHON=""                      # vazio = auto (python3 · python · py -3)
FABER_MODEL_STRONG_CLAUDE="opus"     FABER_MODEL_FAST_CLAUDE="sonnet"
FABER_MODEL_STRONG_CURSOR="…"        FABER_MODEL_FAST_CURSOR="…"
FABER_MODEL_STRONG_CODEX="…"         FABER_MODEL_FAST_CODEX="…"
FABER_APPROVAL_MODE="ticket"         # ticket (padrão v3) · dialog (compat Claude-only)
```

---

## 5. Fase 2 — Motor portátil (Python) e Windows

### 5.1 Fundação (primeira PR, pequena, destrava o CI do Windows)

- `.gitattributes`: `* text=auto`, `*.sh text eol=lf`, `*.py text eol=lf`,
  `*.cmd text eol=crlf`, `*.ps1 text eol=crlf`, binários marcados.
- `faber/lib/faber_paths.py`: `rel_posix(path, root)`, `same_file()`,
  `is_under(path, dir)`; usa `os.path.realpath` + `os.path.normcase` e devolve
  sempre `/`. Testes com `PureWindowsPath` rodam no Linux; testes reais rodam
  no runner Windows.
- `faber/lib/faber_io.py`: `read_text()`/`write_text()` com `utf-8` fixo;
  `read_hook_stdin()` com `utf-8-sig` (remove BOM) e `sys.stdout.reconfigure(encoding="utf-8")`.
  Substitui as 46 chamadas `open()` sem encoding.
- `faber_config.py`: `git_root()` normalizado; procura `faber.env` também por
  `CURSOR_PROJECT_DIR` (o Cursor exporta `CLAUDE_PROJECT_DIR` como alias [V],
  mas não custa).
- Falhar fechado: `read_hook_stdin()` que não parseia → `deny` com motivo, nos
  hooks de permissão (H1/H2). Hoje é `exit 0`.
- CI: job `windows-latest` com `shell: bash` (Git Bash do runner) rodando as
  suítes existentes. Vai quebrar — e é o que se quer: a lista de falhas é o
  backlog da §5.2.

### 5.2 Hooks em Python puro

`faber/hooks/h1_bash_guard.py` … `h7_checkpoint.py` + `faber/hooks/common.py`
(decide/deny/ask/allow, leitura de stdin, normalização de `tool_name` entre
ferramentas: `Bash|PowerShell|Shell` → `shell`; `Write|Edit|MultiEdit|NotebookEdit|apply_patch` → `write`).

- H1: além de git/gh, reconhece a sintaxe equivalente em PowerShell quando a
  ferramenta é `PowerShell` (os comandos `git push …` são idênticos; o que
  muda são redirecionamentos `Out-File`, `Set-Content`, `>` — entram na lista
  `ESCRITA_SHELL`).
- H2: parser de `apply_patch` (Codex) devolvendo a lista de caminhos; o resto
  da regra roda por caminho.
- Lançadores: `faber/bin/faber-hook` (sh, 6 linhas) e `faber-hook.cmd` (8
  linhas). Os `.claude/hooks/h?-*.sh` atuais ficam **uma release** como shims
  que chamam o lançador (compatibilidade com `settings.json` de instalações
  v2), depois saem.
- `test-h1-h2.sh` (82 casos) vira `tests/test_hooks.py` (pytest, sem
  dependência de bash) com os mesmos 82 casos + casos novos: caminhos
  `C:\…`, cwd `C:/…`, BOM, `tool_name: PowerShell`, `tool_name: apply_patch`,
  input inválido → deny.

### 5.3 Scripts → CLI `faber`

`faber/scripts/*.sh` viram subcomandos de um único ponto de entrada Python
(`python -m faber …`, exposto como `faber/bin/faber` + `faber.cmd`):

| Hoje | v3 | Fase |
|---|---|---|
| `lib/config.sh` | `faber.config` (já existe em Python) | 2a |
| `gate-check.sh`, `gate-set.sh`, `transition.sh`, `new-task.sh`, `worktree.sh`, `evidence.sh`, `workflow-unlock.sh` | `faber gate-check` … (caminho crítico de toda demanda) | 2a |
| `board.sh` | `faber board` (chama `gh`; sem `awk`) | 2b |
| `sonar-gate.sh`, `sonar-task.sh`, `sonar-token-check.sh` | `faber sonar …` (`urllib` em vez de `curl`; sem `awk`) | 2b |
| `local-env.sh`, `design-system-check.sh` | `faber local-env`, `faber ds-check` | 2b |
| `dashboard.sh` | `faber dashboard` (venv em `Scripts/` ou `bin/`) | 2b |
| `test-gate-check.sh`, `test-sonar-gate.sh` | pytest | junto de cada um |

Regras da conversão:

- `evidence` executa `FABER_CMD_*` via `subprocess.run(cmd, shell=True,
  executable=FABER_SHELL)`; `FABER_SHELL` auto = `/bin/sh` em POSIX, Git Bash
  se existir no Windows, senão `cmd.exe`. O default `make lint` passa a ser
  escolhido só se `make` existir; senão fica vazio com aviso no `faber.env`.
- Os `.sh` antigos ficam uma release como shims (`exec faber/bin/faber
  gate-check "$@"`) para não quebrar prompts que ainda citem
  `faber/scripts/gate-check.sh`; as 36 citações a `evidence.sh` nas skills são
  trocadas na mesma PR.
- Nomes de arquivo gerados são auditados contra caracteres inválidos em NTFS
  (`: * ? " < > |`): os handoffs `NN-dev-para-cto.md` já são válidos; a
  checagem entra em `faber doctor`.
- `worktree`: após criar, roda `git config core.longpaths true` no Windows.
- Testes com `ln -sf` são reescritos com scripts-shim (sem symlink).

### 5.4 Instalador

- `install.sh` (490 linhas de bash) vira `install.py`. `install.sh` e
  `install.ps1` ficam como wrappers de 5 linhas que resolvem o Python.
- `bootstrap.ps1` para `irm https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.ps1 | iex`
  (mesma lógica: baixa o tarball da ref, roda `install.py`, reanexa o console).
- `bin/faber.js`: remove o `die` em `win32`; resolve Python; delega a
  `install.py`. `package.json` `os` passa a incluir `win32`.
- Novos flags: `--tools claude,cursor,codex` (default: detecta `.cursor/`,
  `.codex/`, `~/.cursor`, `~/.codex`, `~/.claude`), `--git-hooks on|off`.
- Novo passo "adaptadores" (§6) depois do render.
- Mensagem final por OS/ferramenta (como abrir o Codex e confiar nos hooks,
  como ligar o toggle no Cursor, etc.).

### 5.5 `faber doctor` multiplataforma

Checa e explica (nunca corrige em silêncio): interpretador e versão; PyYAML;
`git`, `gh`; no Windows: Git Bash localizado (`CLAUDE_CODE_GIT_BASH_PATH` ou
pastas padrão [V]), `core.autocrlf`, `core.longpaths`; arquivos `.sh` com
CRLF; ferramentas detectadas e estado dos adaptadores (desatualizados em
relação ao `faber.env`?); no Codex, se o projeto está em
`[projects."<path>"] trust_level = "trusted"` [V] e lembra do `/hooks`; no
Cursor, lembra do toggle "third-party" e do workspace confiável [V].

---

## 6. Fase 3 — Adaptadores e distribuição

### 6.1 `faber adapt`

Idempotente; roda no fim do `install` e sempre que `faber.env` mudar
(`faber doctor` avisa quando o hash não bate). Gera, por ferramenta em
`FABER_TOOLS`:

**Claude** — `.claude/settings.json` (hooks em exec-form `bash` + lançador,
matcher `Bash|PowerShell`, permissões como hoje; merge preservado).

**Cursor** — `.cursor/hooks.json` (`version: 1`, eventos da §4.4,
`failClosed: true`, `timeout` generoso — fóruns relatam deny perdido por
timeout curto [F]); `.cursor/agents/*.md`; `.cursor/rules/faber.mdc`
(`alwaysApply: true`, 10 linhas: "este repositório roda a fábrica Faber; a
constituição é AGENTS.md; nunca …"). Decisão sobre desligar a importação dos
hooks do `.claude/settings.json` (para não disparar duas vezes) depende de S2.

**Codex** — `.codex/hooks.json` (com `commandWindows`), `.codex/agents/*.toml`,
`.codex/rules/faber.rules` (`prefix_rule` para `git push`/`git merge`/`gh pr
merge`/`gh api … merge` = `forbidden`; `FABER_REFS_CONFIRM` = `prompt`;
`faber approve` = `forbidden`), `.codex/config.toml` só com o que é
projeto-aceitável ([V] ignora `model_provider`, `notify`, `profile`).

Testes de contrato: para cada adaptador, fixtures de input JSON reais
(capturados nos spikes) → saída esperada; rodam nos três SOs.

### 6.2 Distribuição

| Canal | Hoje | v3 |
|---|---|---|
| Plugin Claude Code (`/plugin marketplace add uhitlei/faber`) | sim | igual; `/faber:install` chama `install.py` |
| Plugin Codex | — | **o mesmo `.claude-plugin/marketplace.json`**: o Codex aceita manifests Claude-compatíveis [V]; as 3 skills (`install`/`update`/`doctor`) funcionam porque só usam shell. Só CLI e app — a extensão IDE não tem plugins [V]; documentar o `bootstrap` como alternativa |
| Plugin Cursor | — | `.cursor-plugin/marketplace.json` + `plugins/faber/.cursor-plugin/plugin.json` apontando `skills/` [V]; mesmo payload |
| `npx @uhitlei/faber` | mac/Linux | + Windows |
| `curl … bootstrap.sh \| bash` | mac/Linux/Git Bash | + `irm … bootstrap.ps1 \| iex` |
| zip de release | sim | + `install.ps1` dentro |

---

## 7. Fase 4 — Matriz de suporte, testes e documentação

### 7.1 Matriz de suporte declarada (vai para o README)

| | Claude Code | Cursor (IDE e CLI) | Codex (CLI, app) | Codex (extensão IDE) |
|---|---|---|---|---|
| macOS | **Tier 1** | Tier 1 | Tier 1 | Tier 2 (sem plugin; bootstrap) |
| Linux (Ubuntu, Fedora) | **Tier 1** | Tier 1 | Tier 1 | Tier 2 |
| Windows 11 + Git for Windows | **Tier 1** | Tier 1 após S2 | Tier 1 | Tier 2 |
| Windows 11 sem Git Bash | não suportado (§9-D1) | Tier 2 após S2 | Tier 1 (`commandWindows`) | Tier 2 |
| WSL2 | = Linux | = Linux | = Linux | = Linux |
| Windows 10 | best effort (o Codex declara o mesmo [V]) | best effort | best effort | best effort |

Tier 1 = testado no CI a cada PR. Tier 2 = testado a cada release, manualmente,
com checklist. Tabela de degradação por ferramenta (o que vira aviso em vez de
bloqueio — §4.4) publicada ao lado.

### 7.2 CI (`ci.yml`)

```
suites:   ubuntu-latest · macos-latest · windows-latest (shell: bash = Git Bash)
          → pytest (hooks, gate-check, sonar, monitor, requirements, adaptadores, paths)
          → dashboard (opcional)
native-windows: windows-latest, shell: pwsh
          → install.ps1 end-to-end num repo sintético; faber doctor; hooks via faber-hook.cmd
install-e2e: matriz 3 SOs × --tools claude,cursor,codex
          → contagens (9 agentes, 12 skills de comando + 10 skills, 7 hooks por adaptador)
          → nenhum @@FABER_@@ sobrando; nenhum .sh com CRLF; nenhum open() sem encoding (lint próprio)
          → hooks disparam no repo instalado (deny em git push main) — nos três formatos de input
lint:     shellcheck (só nos lançadores restantes) · ruff · claude plugin validate · manifests (3 marketplaces coerentes com VERSION)
```

### 7.3 Documentação

- `INSTALL.md`/`INSTALL.pt-BR.md`: uma seção por SO (incluindo "Windows: instale
  o Git for Windows com Git Bash; `py -3` ou `python` no PATH") e uma por
  ferramenta (o que ligar no Cursor; `trust` + `/hooks` no Codex).
- `docs/compatibilidade.md`: matriz §7.1 + degradações §4.4 + o modelo de
  ticket §4.3.
- `CONTRIBUTING.md`: baseline muda de "bash 3.2" para "Python 3.9, sem bash
  fora dos lançadores".
- README: tira "for Claude Code" do subtítulo; "for Claude Code, Cursor and
  Codex".

### 7.4 Migração v2 → v3 (`/faber:update`)

Repositórios já instalados com a v2 recebem, em uma PR gerada pelo update:
`CLAUDE.md` → `AGENTS.md` + ponteiro; `.claude/commands/faber-*.md` → skills
(e remoção dos comandos para não duplicar o `/`); `settings.json` com os
comandos de hook reescritos; `faber.env` com as chaves novas (defaults);
`faber adapt`. `faber doctor` detecta v2 e aponta para o update.

---

## 8. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Cursor não aplica `deny` de forma confiável no Windows (BOM, timeout, race) [F] | média | alto — guarda-vidas furado | `failClosed: true`, timeout alto, hook escreve log de auditoria; S2/S5 medem; se não for confiável, Cursor-Windows fica Tier 2 com aviso explícito no `doctor` |
| Codex marca hook como falho num `ask` esquecido e **roda a ferramenta** [S] | baixa (após §4.3) | alto | lint no CI: nenhum `ask` no adaptador Codex; teste de contrato |
| Claude Code não ler `.agents/skills` | média | médio — dois diretórios de skills | S1 decide; plano B em §4.1 |
| Dupla injeção (CLAUDE.md + AGENTS.md; hooks importados + nativos; skills em dois dirs) no Cursor [F] | alta | médio — custo de contexto, hooks 2× | `CLAUDE.md` = `@AGENTS.md`; S2 decide se desligar a importação; um só dir de skills |
| Subagentes do Codex sem restrição de ferramenta/sandbox [V] | certa | médio — reviewer pode editar | instrução explícita no `developer_instructions`; `features.shell_tool=false` onde cabe; H2 continua negando paths protegidos independentemente de quem edita; anotado na matriz |
| Mapeamento de modelos envelhece (ids do Cursor/Codex mudam) | alta | baixo | chaves em `faber.env`; `doctor` valida contra lista conhecida e avisa |
| Reescrita de 3.700 linhas de bash introduz regressão | média | alto | portar suíte por suíte, mantendo os `.sh` como shims por uma release; os 206 casos atuais são o piso — nenhum pode sumir |
| `apply_patch` muda de formato [I] | baixa | alto | parser com testes de fixture; se não reconhecer o formato → **deny** (fail-closed) |
| Trust do Codex: o Owner esquece de confiar nos hooks após uma edição [V] | alta | alto — hooks silenciosamente off | `doctor` lembra; o instalador imprime o passo; CHANGELOG marca toda release que toca em hooks |
| Caminhos longos / nomes inválidos em NTFS | baixa | médio | `core.longpaths`; auditoria no `doctor`; convenção de nomes documentada |

---

## 9. Decisões que são do Owner

Cada item traz a recomendação; o plano assume a recomendação até ordem
contrária.

- **D1 — Windows sem Git Bash no Claude Code.** O Claude Code sem Git Bash não
  tem ferramenta Bash [V]; todo o modelo do H1 (e todos os comandos que os
  agentes rodam) assume um shell POSIX. Suportar PowerShell puro significaria
  um segundo dialeto em H1 e em todas as skills. **Recomendação:** exigir Git
  for Windows (já exigimos `git`) para o Claude Code; `doctor` detecta a
  ausência e explica. Reavaliar na v3.1 se houver demanda.
- **D2 — Motor em Python.** §2.1. **Recomendação:** sim.
- **D3 — Comandos viram skills** (breaking: `/faber-task` continua existindo,
  mas vem de `skills/`). **Recomendação:** sim; é o único formato comum.
- **D4 — Aprovação por ticket** substitui o diálogo como prova de humano nos
  gates G1/G6/G8 e no unlock de workflows. **Recomendação:** sim, nas três
  ferramentas, com o `ask` do Claude mantido como camada extra.
- **D5 — `AGENTS.md` como constituição**, `CLAUDE.md` ponteiro.
  **Recomendação:** sim.
- **D6 — Versão.** Tudo acima é breaking → **v3.0.0**, com `/faber:update`
  migrando v2.
- **D7 — Ordem das ferramentas.** Codex antes de Cursor: a compatibilidade de
  hooks e de plugin é documentada e mais estável; o Cursor depende de S2/S5.

---

## 10. Sequência e critérios de pronto

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0 Spikes | S1–S5 com evidência | `SPIKES-MULTIPLATAFORMA.md` fechado; §9 revisada |
| 1 Fundação | `.gitattributes`, `faber_paths`, `faber_io`, fail-closed, job Windows (Git Bash) | job Windows **falha de forma conhecida** (lista = backlog); nenhuma regressão em mac/Linux |
| 2a Hooks + caminho crítico | H1–H7 em Python, lançadores, `faber gate-check/gate-set/transition/new-task/worktree/evidence/workflow-unlock`, ticket | 82 + novos casos verdes nos 3 SOs; demanda completa (`/faber-task` → G9) rodada no Windows 11 + Git Bash com evidência |
| 2b Resto do motor + instalador | `faber board/sonar/local-env/ds-check/dashboard`, `install.py`, `bootstrap.ps1`, `faber.js` win32 | install e2e verde nos 3 SOs; `native-windows` verde; shims `.sh` ainda presentes |
| 3 Multi-ferramenta | `AGENTS.md`, skills, adaptadores Cursor/Codex, manifests de plugin, `doctor` | demanda completa rodada no Codex CLI (mac e Windows) e no Cursor (mac; Windows conforme S2) com evidência; testes de contrato verdes |
| 4 Release 3.0 | matriz §7.1 publicada, docs, `/faber:update`, CHANGELOG, zip + ps1 | tag `v3.0.0`; um repo v2 real migrado pelo update sem intervenção manual |
| 3.1 | remoção dos shims `.sh`; Cursor-Windows Tier 1 se S2 permitir | — |

Tamanho relativo: fase 0 = P; 1 = P; 2a = **G**; 2b = G; 3 = M; 4 = M. As
fases 2a e 3 podem andar em paralelo depois da 1, porque tocam arquivos
diferentes (motor vs. prosa/adaptadores) — desde que 2a feche antes dos
testes de contrato da 3.

---

## Anexo A — Fontes consultadas (out/2026)

Claude Code: `code.claude.com/docs/en/setup`, `/hooks`, `/tools-reference`,
`/env-vars`, `/plugins/manifest-reference`.
Cursor: `cursor.com/docs/rules`, `/subagents`, `/skills`, `/hooks`,
`/reference/third-party-hooks`, `/reference/plugins`, `/plugins`, `/mcp`,
`/cli/using`; fóruns 149974, 164295, 161342, 165818, 169942, 165962, 146808,
154608, 151859, 160677.
Codex: `learn.chatgpt.com/docs/agent-configuration/agents-md`, `/custom-prompts`,
`/build-skills`, `/agent-configuration/subagents`, `/hooks`,
`/agent-approvals-security`, `/agent-configuration/rules`,
`/config-file/config-advanced`, `/plugins`, `/windows/windows-sandbox`,
`/extend/mcp`; código-fonte `openai/codex` (HEAD) para `ask` não suportado e
diretórios de skills.
