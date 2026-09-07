# Instalando o Faber

Três portas de entrada. Todas terminam no mesmo lugar: a fábrica renderizada
dentro do seu repositório, na branch `faber/bootstrap`, esperando o `/faber-init`.

> **English:** [INSTALL.md](INSTALL.md)

---

## A. Plugin do Claude Code (recomendado)

```
/plugin marketplace add uhitlei/faber
/plugin install faber@faber
```

Depois, dentro do repositório onde você quer a fábrica:

```
/faber:install
```

O plugin te dá exatamente três comandos — `/faber:install`, `/faber:update`,
`/faber:doctor`. Ele **não** te dá a fábrica. A fábrica é escrita no seu
repositório, renderizada com o nome do seu aprovador, as suas branches e os
seus comandos de validação, e nada nela roda antes disso. É de propósito: uma
fábrica meio instalada aprovaria gates contra a configuração de outra pessoa.

## B. Peça para o Claude fazer

Em qualquer sessão do Claude Code, dentro do repositório que você quer:

> Instale o Faber neste repositório seguindo
> `https://github.com/uhitlei/faber/blob/main/INSTALL.pt-BR.md`

O Claude busca este arquivo e segue a seção D abaixo.

## C. Uma linha de shell

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh | bash
```

Sem interação (CI, scripts) — `--interaction` é obrigatório porque é a única
coisa que o instalador não decide por você:

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh \
  | bash -s -- --yes --interaction gates --owner-name "Ana Silva" --lang pt-BR --trunk develop --main main --gh on
```

Ou clone e rode você mesmo, se jogar a internet dentro do bash não for seu
hábito:

```bash
git clone https://github.com/uhitlei/faber.git && cd faber
./install.sh /caminho/do/seu/repo
```

---

## D. O procedimento, passo a passo

Esta seção é escrita para ser executada literalmente — por uma pessoa ou por
um agente.

### D.1 Pré-requisitos

```bash
git --version
python3 --version
python3 -c "import yaml" && echo "PyYAML ok" || echo "PyYAML AUSENTE"
gh --version | head -1
```

- `git` e `python3` são **obrigatórios**. Pare se faltar um dos dois.
- **PyYAML** é exigido pelo `gate-check`, pelo `board.sh` e pelos hooks:
  `pip3 install pyyaml`.
- `gh` é opcional. Com ele, o ID da demanda é o número da issue no GitHub.
  Sem ele, passe `--gh off` e um contador local assume.

### D.2 Baixar o payload

```bash
TMP="$(mktemp -d)"
curl -fsSL https://codeload.github.com/uhitlei/faber/tar.gz/main | tar -xz -C "$TMP" --strip-components=1
INSTALADOR="$TMP/plugins/faber/install.sh"
```

### D.3 Ver o que ele detecta antes de escrever qualquer coisa

```bash
bash "$INSTALADOR" /caminho/do/seu/repo --dry-run --interaction gates
```

O instalador **não usa modelo**. Ele conta arquivos-fonte, lê manifestos e
procura sinais de Spec Kit, PRD/BRD e brainstorm, e escolhe o modo de
bootstrap por precedência:

| O repositório parece | Modo | O que o bootstrap vai produzir |
|---|---|---|
| ter código e histórico | `existing-repo` | specs globais lidas do código (arquitetura, dados, segurança, CI, testes, convenções), inventário de features e a configuração real (lint/build/test, migrations, paths protegidos) |
| novo, com specs em **Spec Kit** | `spec-kit` | constituição → regras; cada `specs/NNN/spec.md` → SPEC RFC de 17 seções; `plan.md` → arquitetura; `tasks.md` → backlog |
| só um **PRD/BRD** | `prd` | arquitetura `[PROPOSTA]`, specs de feature derivadas dos requisitos, backlog priorizado |
| só um **brainstorm** | `brainstorm` | gera PRD + BRD seguindo o seu guia, para para você aprovar, e segue como `prd` |
| transcrições e notas de reunião (escolha explícita) | `discovery` | o business analyst extrai evidências e requisitos, gera BRD/PRD, resolve lacunas e entrega ao PO |
| nada | `empty` | pergunta qual insumo você vai trazer |

Force um com `--mode <modo>` se a detecção errar.

### D.4 Responder as perguntas

Os defaults saem do repositório. A única pergunta sem default é o **modo de
interação**:

- `gates` — o CTO encadeia o fluxo inteiro e para só em **G1**
  (ready-for-dev), **G6** (sua avaliação), **G8** (merge) e em dúvidas
  críticas. Recomendado.
- `step-by-step` — o CTO para ao fim de cada comando e pede ok.

E o **idioma** em que os agentes trabalham: `--lang pt-BR` ou `--lang en`. Os
dois pacotes estão completos; o contrato de máquina (`state.yaml`, colunas do
board, labels do GitHub) é inglês nos dois casos.

### D.5 Instalar

```bash
bash "$INSTALADOR" /caminho/do/seu/repo --yes \
  --interaction gates \
  --project "Meu Produto" \
  --owner-name "Ana Silva" --owner ana-silva \
  --main main --trunk develop \
  --gh on --specs-dir specs --dashboard off
```

Extras úteis: `--mode <modo>` · `--profile node-web|node-supabase|python|generico`
· `--prd-guide meu-guia.md` (o seu próprio guia de PRD/BRD) · `--labels` (cria as
labels `faber` e `estado:*` no GitHub) · `--force` (sobrescreve os arquivos do
próprio kit; **nunca** toca em `faber/config/faber.env`, `faber/tasks/` nem nas
suas specs).

O que aterrissa no seu repositório está listado no
[README.pt-BR.md](README.pt-BR.md#o-que-é-instalado).

### D.6 Verificar — evidência, não promessa

```bash
cd /caminho/do/seu/repo
bash .claude/hooks/test-h1-h2.sh           # 46 casos: o que os hooks negam, confirmam e liberam
bash faber/scripts/test-gate-check.sh      # 43 casos: transições liberadas e bloqueadas
bash faber/scripts/test-sonar-gate.sh      # 20 casos (módulo Sonar, com curl stubado)
python3 faber/scripts/test-monitor.py      # 40 casos (monitor de estado)
python3 faber/scripts/test-requirements.py # 21 casos (readiness de requisitos)
```

As cinco precisam ficar verdes. Elas criam sandboxes descartáveis e não tocam
no seu repositório. Se alguma falhar, a fábrica não está pronta — leia a saída,
não siga em frente.

Depois prove que o guarda-vidas dispara **no seu** repositório:

```bash
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git push origin $(git symbolic-ref --short HEAD)\"},\"cwd\":\"$PWD\"}" \
  | bash .claude/hooks/h1-bash-guard.sh
```

Tem que responder `"permissionDecision": "deny"`.

### D.7 Concluir o bootstrap

1. Reinicie o Claude Code (ou `/reload-plugins`) para carregar os comandos,
   agentes e skills recém-escritos.
2. `/faber-init` — gera specs, arquitetura e backlog a partir do contexto
   detectado.
3. Faça o merge da PR `faber/bootstrap` na sua branch de integração. **Esse
   merge é o gate de fundação, e ele é seu.**
4. `/faber-task <sua primeira demanda>`.

---

## Atualizar

```
/faber:update
```

ou rode o instalador de novo: arquivos iguais são pulados, diferentes são
mantidos e listados. `--force` sobrescreve os arquivos do kit mas preserva a
sua configuração, as suas demandas e as suas specs.

## Desinstalar

Remova `CLAUDE.md` (ou restaure `CLAUDE.md.bak-faber`), `.claude/agents`,
`.claude/skills`, `.claude/commands`, `.claude/hooks`, os hooks e permissões do
Faber em `.claude/settings.json`, e a pasta `faber/`. A pasta de specs é sua —
fique com ela.

## Diagnóstico

| Sintoma | Causa | Solução |
|---|---|---|
| `Faber nao esta instalado nesta arvore` | um script rodou onde não existe `faber/config/faber.env` | rode `/faber:install`, ou vá para a raiz do repositório |
| os comandos `/faber-*` não aparecem | o Claude Code não recarregou desde a instalação | reinicie, ou `/reload-plugins` |
| `gate-check` falha com erro de YAML | PyYAML ausente | `pip3 install pyyaml` |
| `new-task.sh` não acha o repositório | `gh` ausente ou sem autenticação com `FABER_GH=on` | `gh auth login`, ou defina `FABER_GH="off"` |
| placeholders `@@FABER_*@@` ainda visíveis | a renderização não passou naquele arquivo | reinstale com `--force` e reporte como bug |
