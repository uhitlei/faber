# 02 · Design System

<!-- Projetos sem interface: "não se aplica" na seção 1 e remova o resto
     (FABER_DESIGN_SYSTEM=off). -->

## 1. Fundamentos

- **Biblioteca/base:** {{ex.: shadcn/ui, MUI, componentes próprios}}
- **Tokens:** {{onde vivem (arquivo CSS/theme) e como são consumidos}}
- **Regra de ouro:** zero cor/espaçamento hardcoded — sempre tokens semânticos.

## 2. Tokens semânticos

| Token | Uso | Light | Dark |
|---|---|---|---|
| {{primary}} | {{ação principal}} | {{...}} | {{...}} |

## 3. Tipografia e espaçamento

{{escala tipográfica, grid, breakpoints}}

## 4. Componentes canônicos

| Componente | Quando usar | Onde está |
|---|---|---|
| {{Button}} | {{...}} | {{path}} |

## 5. Estados de interface

- loading · vazio · erro · sucesso — {{padrões e componentes de cada estado}}

## 6. Responsivo

- {{mobile-first? breakpoints? sem overflow horizontal}}

## 7. Acessibilidade

- Alvo de toque ≥ 44×44px · contraste AA · foco visível · navegação por teclado · `aria-*` em componentes customizados.

## 8. Exceções

### 8.1 Como declarar
`// ds-exception: <motivo>` na linha anterior ao trecho (a Skill `design-system-check` lista as exceções para o review julgar).

### 8.2 Exceções justificadas
| Onde | Motivo |
|---|---|
| {{... ou "nenhuma"}} | {{ex.: cor de marca de terceiro}} |
