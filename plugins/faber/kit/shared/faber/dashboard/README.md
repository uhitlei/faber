# Dashboard da fábrica (módulo opcional)

Kanban **somente leitura** das demandas da fábrica, projetado dos `state.yaml`
que já existem em disco, com **telemetria ao vivo dos agentes** lida dos
transcripts JSONL do Claude Code (`~/.claude/projects`). Roda **local**, em
`127.0.0.1`, sob demanda. Flask + Jinja2 + PyYAML + SQLite da stdlib; zero
JavaScript.

É um módulo **opcional**: ligue com `FABER_DASHBOARD="on"` em
`faber/config/faber.env`. Desligado, nada aqui é usado pela fábrica.

## Como rodar

```bash
faber/dashboard/dashboard.sh          # http://127.0.0.1:8099
faber/dashboard/dashboard.sh 9000     # outra porta
faber/dashboard/dashboard.sh --testes # suíte portátil (passa em qualquer instalação)
faber/dashboard/dashboard.sh --testes --faber-real  # observações desta máquina
```

Na primeira execução o script cria `faber/dashboard/.venv` (gitignored) e
instala o `requirements.txt`; nada vai para o Python global, e `-B` +
`PYTHONDONTWRITEBYTECODE=1` impedem `__pycache__` no repositório. A suíte
padrão (`testes/rodar.py`, unittest da stdlib) usa só fixtures sintéticas; o
alvo `--faber-real` mede a fábrica desta máquina (checkouts vivos,
divergência entre cópias) e falha, com razão, numa instalação recém-feita.

## O que mostra

**Kanban** (`/`): as 9 colunas macro lidas de
`faber/templates/state.template.yaml` (`_schema`), o mesmo mapa que o
`board.sh` usa. Card com ID, título, estado, agente atuante, gate corrente,
destaque para `clarification` (aguardando Owner) e `blocked` (com o motivo).
KPIs: em andamento, aguardando Owner, concluídas, canceladas, leituras
inválidas, ao vivo agora, output fora de demanda. Busca por ID ou título
(`?q=`); `cancelled` só aparece em busca explícita.

**Detalhe** (`/faber-task/<id>`): histórico de transições, os 9 gates, todas as
cópias do `state.yaml` encontradas (com a autoritativa marcada), telemetria da
demanda e histórico completo de output, paginado (`?pagina=N`).

**Multi-fonte.** Não existe "a pasta de demandas": cada worktree tem a sua
cópia e cada ref do git carrega um retrato congelado. O leitor varre todos os
checkouts (`git worktree list`) e todas as refs (`for-each-ref` + `cat-file`)
e a cópia autoritativa é a de **maior `atualizada_em`**. Estado fora da lista
fechada do template é **leitura inválida**, nunca estado (um `state.yaml` lido
no meio da escrita parseia e devolve `refi`). Fonte que falhou é **declarada**
na tela ("quadro possivelmente incompleto"), nunca inferida como vazia.

**Telemetria.** A cada request, `telemetria.py` varre incrementalmente os
transcripts do repositório (sessões e `subagents/*.jsonl`, inclusive das
worktrees) e `banco.py` persiste em `dados/telemetria.sqlite` só a **lista
branca** `banco.CAMPOS_PERSISTIVEIS`: `usage`, `requestId`, `gitBranch`,
`timestamp`, `sessionId`, agente, modelo, offsets. Conteúdo de mensagem
**nunca** entra no banco — o output exibido é relido do JSONL e descartado.
Regras que os testes travam:

- atribuição **por linha** (`gitBranch` → `TASK-N`), nunca por arquivo — o
  transcript é da sessão e a sessão troca de demanda;
- dedup por `requestId` com `UPSERT … MAX()`; total por `SUM`, sem acumulador
  (reprocessar não infla);
- transcript removido do disco: tokens **retidos**, conteúdo vira "sem dados";
- indicador **AO VIVO** = atividade nos últimos 90 s, com "há Xs" ao lado;
  auto-refresh de 15 s só quando há demanda ao vivo (`?vivo=0` desliga);
- `thinking` nunca é exibido; branches sem demanda (`develop`, `release/…`)
  contam só no KPI "fora de demanda", nunca são rateadas.

O banco é cache descartável: `rm -rf faber/dashboard/dados/` e recarregar
devolve o mesmo quadro (há teste para isso). Diagnóstico em linha de comando:
`.venv/bin/python -B faber/dashboard/leitor.py` e `... banco.py`.

## Segurança e trava de deploy

- **Bind fixo em `127.0.0.1`** (decisão do Owner); não há opção de host.
  Requests com `Host` fora de `127.0.0.1`/`localhost`/`[::1]` recebem 403
  (DNS rebinding). `debug=False` sempre. Autoescape do Jinja2 em tudo; nenhum
  template usa `|safe`.
- **Somente leitura** do estado da fábrica: nenhuma rota escreve em
  `state.yaml`, issue, board ou transcript (teste com impressão digital
  sha256 antes/depois de todas as rotas).
- **Sem `python-dotenv`**, de propósito: ele carregaria o `.env` do produto
  (chaves e segredos) num processo que não precisa deles.
- **`trava_deploy.py`**: falha se qualquer vestígio do dashboard aparecer no
  artefato de build (`dist/`) ou for referenciado pelas fontes do build
  (`src/`, `public/`, `index.html`, `vite.config.ts` — ajuste
  `FONTES_DO_BUILD` à sua stack). Procura o canário
  `FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH` (plantado em `app.py`, `leitor.py`,
  `banco.py`, `telemetria.py`, CSS e `base.html`), a string
  `faber/dashboard` e o banco `telemetria.sqlite*`. O que não lê (binário,
  arquivo > 8 MB) é **declarado** na saída.

```bash
<build do produto> && faber/dashboard/.venv/bin/python -B faber/dashboard/trava_deploy.py
# exit 0 = ok · 2 = vazou para o artefato · 1 = não executado (dist ausente)
```

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `leitor.py` | fontes (checkouts + refs), leitura tolerante, resolução, projeção e KPIs |
| `telemetria.py` | descoberta de transcripts, leitura incremental, extração, atribuição por linha |
| `banco.py` | **único** importador de `sqlite3`: esquema, lista branca, varredura e consultas |
| `app.py` | 2 rotas GET (`/` e `/faber-task/<id>`), bind 127.0.0.1, checagem de `Host` |
| `trava_deploy.py` | trava verificada contra vazamento para o build |
| `templates/`, `static/` | Jinja2 + CSS escrito à mão, sem build step; `dados/` = banco local (gitignored) |
| `testes/rodar.py` | suíte portátil (unittest da stdlib; sem pytest) |
| `testes/teste_canario.py` | trava de privacidade da persistência — **bloqueante** |
| `testes/faber_real.py` | observações da máquina de trabalho (`--faber-real`) |

O leitor **importa** `faber/scripts/monitor.py` (ordem dos gates, fila do
Owner, numeração) e nunca o edita. `telemetria.py` não conhece persistência
(não importa `sqlite3` nem `banco`) — há teste estático cobrando isso.

## Limites conhecidos

- A cópia autoritativa e o limiar de 90 s pressupõem relógio coerente entre
  as fontes e a máquina local. Uma ferramenta longa (build, E2E) deixa o
  transcript mudo por mais de 90 s e o AO VIVO apaga; o "há Xs" explica.
- Rodando de dentro de um worktree, o dashboard acha o checkout principal via
  `git rev-parse --git-common-dir`; fechar o worktree mata o processo.
- O detalhe relê os transcripts inteiros e só então pagina: o custo cresce com
  o histórico. Banco corrompido degrada visivelmente e não se auto-recupera —
  apague `dados/`.
