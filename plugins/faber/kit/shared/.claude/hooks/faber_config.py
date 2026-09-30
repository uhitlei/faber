"""faber_config.py — leitor de faber/config/faber.env para os hooks.

Parser mínimo (sem dependências): linhas KEY="valor" ou KEY=valor; ignora
comentários e linhas vazias; remove comentário inline após o valor quotado.
Nunca faz `source` (sem execução de shell). Defaults idênticos aos de
faber/scripts/lib/config.sh — manter os dois em sincronia.
"""
import os
import re
import subprocess

DEFAULTS = {
    "FABER_PROJECT": "Projeto",
    "FABER_OWNER": "owner",
    "FABER_OWNER_NAME": "Owner",
    "FABER_LANG": "pt-BR",
    "FABER_REMOTE": "origin",
    "FABER_TRUNK": "develop",
    "FABER_MAIN": "main",
    "FABER_WORKTREES": "on",
    "FABER_INTERACTION": "gates",
    "FABER_BYPASS": "on",
    "FABER_GH": "on",
    "FABER_GH_REPO": "",
    "FABER_BOARD": "off",
    "FABER_SPECS_DIR": "specs",
    "FABER_CMD_LINT": "npm run lint",
    "FABER_CMD_BUILD": "npm run build",
    "FABER_CMD_TEST": "npm run test",
    "FABER_E2E": "off",
    "FABER_CMD_E2E": "npx playwright test",
    "FABER_E2E_CMD_REGEX": r"playwright\S*\s+test\b",
    "FABER_E2E_SUMMARY_REGEX": r"\d+\s+passed\b",
    "FABER_E2E_FAIL_REGEX": r"\d+\s+failed\b",
    "FABER_MIGRATIONS_DIR": "",
    "FABER_MIGRATION_CHECKS": "",
    "FABER_PROTECTED_PATHS": "",
    "FABER_SECRET_FILES": ".env,.env.local",
    "FABER_REFS_DENY": "",
    "FABER_REFS_CONFIRM": "",
    "FABER_CMDS_DENY": "",
    "FABER_CMDS_CONFIRM": "",
    "FABER_SONAR": "off",
    "FABER_SONAR_PROJECT_KEY": "",
    "FABER_LOCAL_ENV": "off",
    "FABER_DESIGN_SYSTEM": "off",
    "FABER_DASHBOARD": "off",
}

_LINHA = re.compile(r'^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$')


def git_root(cwd):
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _valor(bruto):
    bruto = bruto.strip()
    if not bruto:
        return ""
    if bruto[0] in "\"'":
        q = bruto[0]
        fim = bruto.find(q, 1)
        return bruto[1:fim] if fim > 0 else bruto[1:]
    return bruto.split("#", 1)[0].strip()


def carregar(cwd=None):
    """Devolve dict com DEFAULTS sobrescritos pelo faber.env encontrado."""
    cfg = dict(DEFAULTS)
    cwd = cwd or os.getcwd()
    candidatos = []
    root = git_root(cwd)
    if root:
        candidatos.append(os.path.join(root, "faber", "config", "faber.env"))
    pd = os.environ.get("CLAUDE_PROJECT_DIR")
    if pd:
        candidatos.append(os.path.join(pd, "faber", "config", "faber.env"))
    candidatos.append(os.path.join(cwd, "faber", "config", "faber.env"))
    for p in candidatos:
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    for linha in fh:
                        if not linha.strip() or linha.lstrip().startswith("#"):
                            continue
                        m = _LINHA.match(linha)
                        if m:
                            cfg[m.group(1)] = _valor(m.group(2))
            except OSError:
                pass
            cfg["_path"] = p
            cfg["_root"] = root or os.path.dirname(os.path.dirname(os.path.dirname(p)))
            return cfg
    cfg["_path"] = None
    cfg["_root"] = root
    return cfg


def lista(cfg, chave):
    """Lista separada por vírgula → itens não vazios."""
    return [i.strip() for i in (cfg.get(chave) or "").split(",") if i.strip()]


def regexes(cfg, chave):
    """Lista de regex separadas por ' ;; ' → padrões compilados válidos."""
    out = []
    for bruto in (cfg.get(chave) or "").split(";;"):
        bruto = bruto.strip()
        if not bruto:
            continue
        try:
            out.append(re.compile(bruto, re.I))
        except re.error:
            pass
    return out


def ligado(cfg, chave):
    return str(cfg.get(chave, "")).strip().lower() in ("on", "true", "1", "sim", "yes")


def em_bypass(data, cfg):
    """Sessão em modo bypass (permission_mode=bypassPermissions) E a fábrica
    honra o modo (FABER_BYPASS=on, o padrão). Nesse caso H1/H2 não pedem
    confirmação: o que seria 'ask' vira passagem livre ou deny — exceto o
    registro de gate humano (G1/G6/G8), que continua 'ask'."""
    return (data or {}).get("permission_mode") == "bypassPermissions" \
        and ligado(cfg, "FABER_BYPASS")


def branches_protegidas(cfg):
    """Trunk e main, nas variantes de caixa mais comuns."""
    nomes = set()
    for b in (cfg.get("FABER_TRUNK"), cfg.get("FABER_MAIN")):
        if b:
            nomes.update({b, b.lower(), b.capitalize()})
    nomes.update({"main", "master"})
    return sorted(nomes)
