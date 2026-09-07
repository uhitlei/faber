---
name: design-system-check
description: An executable design-system checklist (optional module FABER_DESIGN_SYSTEM=on) — runs the hardcoded-colour grep (design-system-check.sh) and guides the manual checklist (44px, dark + light, mobile, component reuse). Use in the product-designer and the code-reviewer. Zero hardcoded colour is the golden rule.
---

# design-system-check — conformance with the design system

Source: `faber/ARCHITECTURE.md` §11; spec
`@@FABER_SPECS_DIR@@/global/02-DESIGN-SYSTEM.md` (the golden rule: **zero
hardcoded colour** — only the design system's semantic tokens declared in
`02-DESIGN-SYSTEM.md`, e.g. the utility classes `bg-primary`, `text-foreground`,
`border-border`). Deterministic mechanics:
`faber/scripts/design-system-check.sh` (zero LLM). Optional module:
`FABER_DESIGN_SYSTEM=on` in `faber/config/faber.env`; with it off, Part 1 comes
out as `not-executed` and the opinion rests on Part 2. Language: `FABER_LANG`.

## Part 1 — automated (grep → evidence)

Run it through `evidence.sh` (scope = the demand's diff against
`@@FABER_TRUNK@@`, or explicit paths):

```bash
faber/scripts/evidence.sh TASK-XXX ds-check -- faber/scripts/design-system-check.sh
```

It catches: a **hex colour in an arbitrary class** `[#...]`, **absolute
utilities** `text/bg/border-white|black`, and a **colour literal inside an
arbitrary value** (`text-[hsl(0_0%_100%)]` is the same white as `text-white`,
just in another syntax). `hsl(var(--token))` is **not** a violation — legitimate
token use stays allowed.

Output: `HARDCODE_VIOLATIONS` + `DECLARED_EXCEPTIONS` + `VERDICT`, exit 0/2/3:

| Verdict | Meaning | Action |
|---|---|---|
| `compliant` | zero violations, zero exceptions | carry on |
| `compliant-with-exceptions` | zero violations, but there is a **declared and listed** exception | **read the exceptions**; each one must be justified in `02-DESIGN-SYSTEM.md` (the exceptions section; e.g. a third party's brand colour). An unjustified exception is a rejection |
| `non-compliant` | there is a violation | swap it for a semantic token **before G5** |
| `not-executed` | the tool is unavailable or the module is off | record it explicitly (§15), never infer |

A **declared exception** (`// ds-exception: <reason>`) opens a range to the end
of the block. It is never hidden: the script **lists** the lines it covers, so
the review can judge them. A gate that cannot see the exception says "compliant"
by form, not by substance.

## Part 2 — manual (the grep cannot see rendered layout)

The script does **not** cover these — check them by hand and record them in your
opinion:

1. **Reuse first:** does the component already exist in the project's component
   library (named in `02-DESIGN-SYSTEM.md`)? Do not create a new pattern when a
   suitable one exists.
2. **44×44px** touch targets on buttons and clickable icons.
3. **Dark + light:** colour only through a token (never fixed) in both themes —
   Part 1 helps, but confirm it visually.
4. **Mobile-first:** responsive, with no horizontal overflow.
5. **AA contrast:** pair `*-foreground` with its matching base colour.
