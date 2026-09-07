"""Discovery v1: validação estrutural e revisão dos artefatos; não avalia verdade."""
import hashlib
import json
import re
from pathlib import Path

import yaml

INPUTS = ("sources.yaml", "evidence.yaml", "model.yaml", "assessment.yaml")
OUTPUTS = ("BRD.md", "PRD.md", "speckit/spec.md")
# peso, verificação. Total = 100; somente data/integrations admitem N/A.
CRITERIA = {
    "problem": (7.5, "Problema, contexto atual e impacto identificados"),
    "objectives": (7.5, "Objetivos e resultados de negócio verificáveis"),
    "users": (5, "Usuários e stakeholders identificados"),
    "permissions": (5, "Responsabilidades e acesso esclarecidos"),
    "scope": (7.5, "Escopo da entrega delimitado"),
    "out_of_scope": (7.5, "Exclusões e limites explícitos"),
    "workflows": (7.5, "Fluxos principais e exceções descritos"),
    "rules": (7.5, "Regras de negócio e condições esclarecidas"),
    "functional": (7.5, "Requisitos necessários, atômicos e consistentes"),
    "dependencies": (7.5, "Dependências e prioridades justificadas"),
    "acceptance": (7.5, "Critérios de aceite verificáveis em cada requisito"),
    "edge_cases": (7.5, "Cenários negativos e de borda verificáveis"),
    "data": (2.5, "Dados, origem, retenção e transição avaliados"),
    "integrations": (2.5, "Integrações e falhas avaliadas"),
    "quality": (2.5, "Qualidades relevantes possuem limites verificáveis"),
    "risks": (2.5, "Riscos, restrições e viabilidade avaliados"),
    "traceability": (2.5, "Requisitos e decisões rastreiam a fontes"),
    "source_coverage": (2.5, "Cobertura das fontes e versões revisada"),
}


class Invalid(ValueError):
    pass


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Invalid(f"{path}: esperado objeto YAML")
    return value


def objects(value, label):
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise Invalid(f"{label}: esperado lista de objetos")
    ids = [x.get("id") for x in value]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise Invalid(f"{label}: IDs ausentes ou duplicados")
    return {x["id"]: x for x in value}


def required(folder, state=None):
    cfg = (state or {}).get("discovery")
    if cfg is not None:
        if not isinstance(cfg, dict) or type(cfg.get("required")) is not bool:
            raise Invalid("state.discovery.required deve ser booleano")
    return (Path(folder) / "requirements").exists() or bool(cfg and cfg["required"])


def evaluate(folder):
    base = Path(folder).resolve()
    reqdir = base / "requirements"
    errors = []
    snapshots = {}
    def fail(message):
        errors.append(message)
    def refs(value, known, label, nonempty=True):
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
            fail(f"{label}: esperado lista de referências")
        elif (nonempty and not value) or any(x not in known for x in value):
            fail(f"{label}: referência ausente ou desconhecida")
    def text(value):
        return isinstance(value, str) and bool(value.strip()) and "{{" not in value
    try:
        docs = {}
        for name in INPUTS:
            p = reqdir / name
            docs[name] = read(p)
            snapshots[name] = sha(p)
            if type(docs[name].get("schema_version")) is not int or docs[name]["schema_version"] != 1:
                fail(f"{name}: schema_version deve ser 1")
        sources = objects(docs["sources.yaml"].get("sources"), "sources")
        evidence = objects(docs["evidence.yaml"].get("evidence"), "evidence")
        model = docs["model.yaml"]
        requirements = objects(model.get("requirements"), "requirements")
        if not sources or not evidence or not requirements:
            fail("Fontes, evidências e requisitos não podem estar vazios")
        if type(model.get("revision")) is not int or model["revision"] < 1:
            fail("model.revision deve ser inteiro positivo")
        for sid, src in sources.items():
            if src.get("kind") not in ("transcript", "notes", "document", "decision", "audio"):
                fail(f"{sid}: tipo de fonte inválido")
            if type(src.get("required")) is not bool:
                fail(f"{sid}: required deve ser booleano")
            if src.get("coverage") not in ("full", "partial", "pending", "excluded"):
                fail(f"{sid}: cobertura inválida")
            if src.get("required") and src.get("coverage") != "full":
                fail(f"{sid}: fonte obrigatória com cobertura incompleta")
            if src.get("required") is False and not text(src.get("exclusion_reason")):
                fail(f"{sid}: exclusão precisa de justificativa")
            source_path = src.get("path")
            if not text(source_path):
                fail(f"{sid}: path ausente")
                continue
            path = Path(source_path)
            if not path.is_absolute():
                path = base / path
            actual = sha(path)
            snapshots[f"source:{sid}"] = actual
            if actual != src.get("sha256"):
                fail(f"{sid}: SHA-256 não confere; revisar fonte e atualizar seus derivados")
            if src.get("kind") == "audio" and src.get("required"):
                transcript = sources.get(src.get("transcript_source"), {})
                if transcript.get("kind") != "transcript" or transcript.get("coverage") != "full" or transcript.get("required") is not True:
                    fail(f"{sid}: áudio obrigatório precisa de transcrição integral obrigatória")
        for eid, ev in evidence.items():
            src = sources.get(ev.get("source"), {})
            if not src or src.get("kind") == "audio" or src.get("coverage") not in ("full", "partial"):
                fail(f"{eid}: fonte textual inexistente ou não analisada")
            if not text(ev.get("locator")) or not text(ev.get("quote")):
                fail(f"{eid}: citação e localização obrigatórias")
            if ev.get("kind") not in ("statement", "decision", "inference"):
                fail(f"{eid}: classificação inválida")
        acceptance_ids = set()
        active = []
        for rid, req in requirements.items():
            status = req.get("status")
            if status not in ("draft", "proposed", "validated", "approved", "rejected", "deprecated"):
                fail(f"{rid}: status inválido")
            if status in ("rejected", "deprecated"):
                if not text(req.get("reason")):
                    fail(f"{rid}: remoção de escopo precisa de motivo")
                continue
            active.append(rid)
            if status not in ("validated", "approved"):
                fail(f"{rid}: requisito ainda não validado")
            if req.get("type") not in ("business", "stakeholder", "functional", "nonfunctional", "transition"):
                fail(f"{rid}: tipo inválido")
            if not text(req.get("statement")):
                fail(f"{rid}: enunciado ausente")
            refs(req.get("evidence"), evidence, rid)
            if isinstance(req.get("evidence"), list):
                kinds = {evidence.get(e, {}).get("kind") for e in req["evidence"] if isinstance(e, str)}
                if not kinds & {"statement", "decision"}:
                    fail(f"{rid}: inferência sem sustentação explícita")
                if status == "approved" and "decision" not in kinds:
                    fail(f"{rid}: aprovação exige evidência de decisão humana")
            refs(req.get("dependencies"), requirements, f"{rid}.dependencies", False)
            if isinstance(req.get("dependencies"), list):
                for dep in req["dependencies"]:
                    if dep == rid or requirements.get(dep, {}).get("status") in ("rejected", "deprecated"):
                        fail(f"{rid}: dependência {dep} inválida para requisito ativo")
            acs = objects(req.get("acceptance_criteria"), f"{rid}.acceptance_criteria")
            if not acs:
                fail(f"{rid}: sem critérios de aceite")
            for aid, ac in acs.items():
                if aid in acceptance_ids or aid in requirements or aid in evidence or not text(ac.get("statement")):
                    fail(f"{rid}: critério {aid} duplicado ou sem enunciado")
                acceptance_ids.add(aid)
        if not active:
            fail("Nenhum requisito ativo")
        if set(sources) & set(evidence) or set(requirements) & (set(sources) | set(evidence)):
            fail("IDs globais não podem colidir")
        # Uma declaração de resolução requer evidência, não apenas um status.
        for group, closed in (("questions", "resolved"), ("conflicts", "resolved"), ("assumptions", "validated")):
            records = objects(model.get(group), group)
            for ident, row in records.items():
                if not text(row.get("statement")):
                    fail(f"{ident}: descrição ausente")
                if row.get("severity") not in ("blocker", "high", "medium", "low"):
                    fail(f"{ident}: severidade inválida")
                if row.get("status") not in ("open", closed):
                    fail(f"{ident}: status inválido")
                if row.get("status") == closed:
                    refs(row.get("resolution_evidence"), evidence, f"{ident}.resolution_evidence")
                elif row.get("severity") in ("blocker", "high"):
                    fail(f"{ident}: pendência crítica aberta")
        checks = docs["assessment.yaml"].get("checks")
        if not isinstance(checks, dict) or set(checks) != set(CRITERIA):
            raise Invalid("assessment.checks deve conter exatamente as verificações da rubrica v1")
        earned = possible = 0.0
        for name, (weight, _) in CRITERIA.items():
            check = checks[name]
            if not isinstance(check, dict):
                raise Invalid(f"assessment.{name}: esperado objeto")
            status = check.get("status")
            if status not in ("missing", "partial", "verified", "not-applicable"):
                fail(f"{name}: status de avaliação inválido")
            if status != "missing":
                if not text(check.get("reason")):
                    fail(f"{name}: justificativa obrigatória")
                refs(check.get("evidence"), evidence, f"assessment.{name}")
            if status == "not-applicable" and name in ("data", "integrations"):
                continue
            if status == "not-applicable":
                fail(f"{name}: esta verificação não admite não aplicabilidade")
            possible += weight
            earned += weight * {"verified": 1, "partial": 0.5}.get(status, 0)
        score = 100 * earned / possible
        if score < 95:
            fail(f"Completude {score:.2f} abaixo de 95")
        return {"schema_version": 1, "score": score, "ready": not errors,
                "errors": errors, "input_hash": digest(snapshots),
                "revision": model.get("revision"), "active_requirements": active}
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        return {"schema_version": 1, "score": None, "ready": False,
                "errors": errors + [str(exc)], "input_hash": None}


def output_hashes(folder):
    base = Path(folder)
    paths = [base / "requirements" / x for x in OUTPUTS]
    # Bootstrap não tem spec de demanda/refinamento. Demandas exigem ambos.
    if (base / "state.yaml").exists():
        paths += [base / "spec.md", base / "refinement.md"]
    hashes = {}
    for p in paths:
        if not p.is_file() or p.stat().st_size == 0:
            raise Invalid(f"Artefato ausente/vazio: {p}")
        if "{{" in p.read_text(encoding="utf-8"):
            raise Invalid(f"Placeholder não preenchido: {p}")
        hashes[str(p.relative_to(base))] = sha(p)
    return hashes


def seal(folder):
    report = evaluate(folder)
    if not report["ready"]:
        raise Invalid("; ".join(report["errors"]))
    hashes = output_hashes(folder)
    # IDs devem sobreviver nas projeções de produto; sem julgar equivalência textual.
    for name in ("requirements/PRD.md", "requirements/speckit/spec.md") + (("spec.md",) if (Path(folder) / "state.yaml").exists() else ()):
        content = (Path(folder) / name).read_text(encoding="utf-8")
        if any(not re.search(r"(?<![\w-])" + re.escape(rid) + r"(?![\w-])", content) for rid in report["active_requirements"]):
            raise Invalid(f"{name}: falta ID de requisito ativo")
    manifest = {"schema_version": 1, "input_hash": report["input_hash"],
                "revision": report["revision"], "outputs": hashes}
    (Path(folder) / "requirements" / "delivery.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def delivery_hash(folder):
    report = evaluate(folder)
    if not report["ready"]:
        raise Invalid("; ".join(report["errors"]))
    manifest = read(Path(folder) / "requirements" / "delivery.json")
    if manifest.get("schema_version") != 1 or manifest.get("input_hash") != report["input_hash"] or manifest.get("revision") != report["revision"]:
        raise Invalid("Selo de entrega ausente/desatualizado; revisar e selar novamente")
    if manifest.get("outputs") != output_hashes(folder):
        raise Invalid("Artefatos alterados após o selo; reconciliar modelo e documentos")
    return digest(manifest)
