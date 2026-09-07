# 02 · Design system

<!-- Projects with no interface: "not applicable" in section 1, and remove the
     rest (FABER_DESIGN_SYSTEM=off). -->

## 1. Fundamentals

- **Library / base:** {{e.g. shadcn/ui, MUI, in-house components}}
- **Tokens:** {{where they live (a CSS or theme file) and how they are consumed}}
- **The golden rule:** zero hardcoded colour or spacing — always semantic tokens.

## 2. Semantic tokens

| Token | Use | Light | Dark |
|---|---|---|---|
| {{primary}} | {{the primary action}} | {{...}} | {{...}} |

## 3. Typography and spacing

{{the type scale, the grid, the breakpoints}}

## 4. Canonical components

| Component | When to use it | Where it is |
|---|---|---|
| {{Button}} | {{...}} | {{path}} |

## 5. Interface states

- loading · empty · error · success — {{the patterns and components for each state}}

## 6. Responsiveness

- {{mobile-first? breakpoints? no horizontal overflow}}

## 7. Accessibility

- Touch targets ≥ 44×44px · AA contrast · visible focus · keyboard navigation ·
  `aria-*` on custom components.

## 8. Exceptions

### 8.1 How to declare one
`// ds-exception: <reason>` on the line before the excerpt (the
`design-system-check` skill lists the exceptions so the review can judge them).

### 8.2 Justified exceptions
| Where | Reason |
|---|---|
| {{... or "none"}} | {{e.g. a third party's brand colour}} |
