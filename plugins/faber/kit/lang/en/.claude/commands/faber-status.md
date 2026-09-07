---
description: The consolidated state of one demand (or all of them), read from disk and from GitHub — never from the session's memory
argument-hint: "[TASK-XXX]"
---

# /faber-status

Argument (optional): **$ARGUMENTS**

Everything is read **now, from disk and from `gh`** — what is not there did not
happen. Shortcut with no LLM: `python3 faber/scripts/monitor.py --once` (a
snapshot) or without `--once` (a live monitor in the terminal).

**With no argument (overview):**
1. List `faber/tasks/TASK-*/state.yaml`; for each one: the task, its type, its
   state, the last entry in `history`, and the block (if any).
2. Highlight **@@FABER_OWNER_NAME@@'s queue** (batching, §20): demands stopped
   at a human gate — `ready-for-dev` awaiting G1, `my-review` awaiting G6,
   `pr-open` awaiting G8 — with each issue's link.
3. If `faber/bootstrap/CONTEXT.md` says `status: pending`, say that the
   factory's bootstrap has not been completed yet (`/faber-init`).

**With TASK-XXX:**
1. `state.yaml`: state, block, the last 3 transitions in `history`, the table of
   the 9 gates (status/approver/evidence), and `ui_impact`.
2. `faber/scripts/board.sh status <issue#>` (the real column plus labels; a
   no-op when `FABER_GH=off`).
3. `gh issue view <issue#> --comments` (the last 3 comments) — when `FABER_GH=on`.
4. The handoff with the highest numeric prefix in `handoffs/` (if there is one):
   its `suggested_next_action` and `open_issues`.
5. Any divergence between the projections (state × board × issue)? Point it out
   and suggest reconciling through `board.sh` — `state.yaml` is the source of
   truth (§6.1).

Format: a short table plus at most 5 lines of prose stating the next action.
