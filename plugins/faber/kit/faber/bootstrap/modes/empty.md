# Modo `empty` — nenhum insumo detectado

O repositório não tem código relevante, nem specs, nem PRD/BRD, nem
brainstorm. A fábrica está instalada, mas não tem do que partir.

## O que fazer

1. Pergunte a @@FABER_OWNER_NAME@@ (uma rodada, opções fechadas):
   - **(a)** vai trazer um arquivo de brainstorm (`docs/brainstorm.md`) → modo `brainstorm`;
   - **(b)** vai trazer um PRD/BRD (`docs/PRD.md`) → modo `prd`;
   - **(c)** vai trazer specs no formato Spec Kit → modo `spec-kit`;
   - **(d)** quer **ditar agora, no chat**, a ideia do produto em algumas
     frases → você grava **literalmente** em `docs/brainstorm.md` (sem
     interpretar) e segue o modo `brainstorm`;
   - **(e)** o repositório receberá código de outro lugar antes → parar; rodar
     `/faber-init --mode existing-repo` depois.
2. Ao receber o insumo, atualize `faber/bootstrap/CONTEXT.md` (`modo`,
   arquivos de entrada) e siga o playbook correspondente.
3. Se o Owner só quiser abrir uma primeira demanda sem base de conhecimento:
   explique que a fábrica funciona melhor com specs, mas é possível — marque o
   bootstrap como `concluido (mínimo)` e deixe as globais como esqueleto com
   `[A DEFINIR]`; a primeira demanda `feature` vai exigir do PO um esforço
   maior de clarificação (§6.2).
