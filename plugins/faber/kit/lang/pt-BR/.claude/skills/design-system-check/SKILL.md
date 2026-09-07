---
name: design-system-check
description: Checklist executável do Design System (módulo opcional FABER_DESIGN_SYSTEM=on) — roda o grep de cor hardcoded (design-system-check.sh) e guia o checklist manual (44px, dark+light, mobile, reuso de componente). Use no product-designer e no code-reviewer. Zero cor hardcoded é a regra de ouro.
---

# design-system-check — conformidade com o Design System

Fonte: `faber/ARCHITECTURE.md` §11; spec `@@FABER_SPECS_DIR@@/global/02-DESIGN-SYSTEM.md`
(regra de ouro: **zero cor hardcoded** — só os tokens semânticos do Design
System declarados em `02-DESIGN-SYSTEM.md`, ex.: classes utilitárias
`bg-primary`, `text-foreground`, `border-border`). Mecânica determinística:
`faber/scripts/design-system-check.sh` (zero LLM). Módulo opcional:
`FABER_DESIGN_SYSTEM=on` em `faber/config/faber.env`; desligado → a Parte 1
sai como `not-executed` e o parecer se apoia na Parte 2. PT-BR (P6).

## Parte 1 — automática (grep → evidência)

Rode via `evidence.sh` (escopo = diff da demanda vs `@@FABER_TRUNK@@`, ou
paths explícitos):

```bash
faber/scripts/evidence.sh TASK-XXX ds-check -- faber/scripts/design-system-check.sh
```

Pega: cor **hex em classe arbitrária** `[#...]`, **utilitárias absolutas**
`text/bg/border-white|black` e **literal de cor em valor arbitrário**
(`text-[hsl(0_0%_100%)]` é o mesmo branco que `text-white`, só noutra sintaxe).
`hsl(var(--token))` **não** é violação — uso legítimo de token continua liberado.

Saída: `HARDCODE_VIOLATIONS` + `DECLARED_EXCEPTIONS` + `VERDICT`, exit 0/2/3:

| Veredito | Significado | Ação |
|---|---|---|
| `conforme` | zero violação, zero exceção | segue |
| `compliant-with-exceptions` | zero violação, mas há exceção **declarada e listada** | **leia as exceções**; cada uma precisa estar justificada em `02-DESIGN-SYSTEM.md` (seção de exceções; ex.: cor de marca de terceiro). Exceção não justificada = reprova |
| `non-compliant` | há violação | troque por token semântico **antes do G5** |
| `not-executed` | ferramenta indisponível ou módulo desligado | registre explícito (§15), jamais infira |

**Exceção declarada** (`// ds-exception: <motivo>`) abre uma faixa até o fim do
bloco. Ela nunca é escondida: o script **lista** as linhas cobertas, para o
review poder julgá-las. Um gate que não enxerga a exceção diz "conforme" por
forma, não por substância.

## Parte 2 — manual (o grep não vê layout renderizado)

O script **não** cobre estes — confira à mão e registre no parecer:

1. **Reuso primeiro:** o componente já existe na biblioteca de componentes do
   projeto (indicada em `02-DESIGN-SYSTEM.md`)? Não crie padrão novo se há um
   adequado.
2. **44×44px** de alvo de toque em botões/ícones clicáveis.
3. **Dark + light:** cor só via token (nunca fixa) nos dois temas — a Parte 1 ajuda,
   mas confirme visualmente.
4. **Mobile-first:** responsivo, sem overflow horizontal.
5. **Contraste AA:** pareie `*-foreground` com a cor base correspondente.
