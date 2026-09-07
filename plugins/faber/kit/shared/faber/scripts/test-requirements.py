#!/usr/bin/env python3
"""Testes técnicos com dados sintéticos; não avaliam a análise de reuniões."""
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from requirements import CRITERIA, Invalid, delivery_hash, evaluate, required, seal, sha


class RequirementsGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.req = self.base / "requirements"
        self.req.mkdir()
        (self.base / "notes.txt").write_text("Decisão: exportar relatório em CSV.\n")
        self.docs = {
            "sources": {"schema_version": 1, "sources": [{"id": "SRC-001", "kind": "notes", "path": "notes.txt", "sha256": sha(self.base / "notes.txt"), "required": True, "coverage": "full"}]},
            "evidence": {"schema_version": 1, "evidence": [{"id": "EV-001", "source": "SRC-001", "locator": "linha 1", "quote": "exportar relatório em CSV", "kind": "decision"}]},
            "model": {"schema_version": 1, "revision": 1, "requirements": [{"id": "REQ-001", "type": "functional", "statement": "Exportar relatório em CSV.", "status": "validated", "evidence": ["EV-001"], "dependencies": [], "acceptance_criteria": [{"id": "AC-001", "statement": "Exportação contém cabeçalho e uma linha por registro."}]}], "questions": [], "conflicts": [], "assumptions": []},
            "assessment": {"schema_version": 1, "checks": {k: {"status": "verified", "reason": "Fixture sintética para testar estrutura, não qualidade da análise.", "evidence": ["EV-001"]} for k in CRITERIA}},
        }
        self.save()
        for name in ("BRD.md", "PRD.md", "speckit/spec.md"):
            p = self.req / name
            p.parent.mkdir(exist_ok=True)
            p.write_text("# Fixture\nREQ-001 — Exportação CSV.\n")

    def save(self):
        for key, data in self.docs.items():
            (self.req / f"{key}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))

    def blocked(self):
        self.save()
        self.assertFalse(evaluate(self.base)["ready"])

    def test_valid_seal_and_fingerprint(self):
        self.assertEqual(evaluate(self.base)["score"], 100)
        seal(self.base)
        self.assertEqual(len(delivery_hash(self.base)), 64)

    def test_empty_templates_fail_closed(self):
        self.docs["model"]["requirements"] = []
        self.blocked()

    def test_partial_required_source_blocks_even_at_100(self):
        self.docs["sources"]["sources"][0]["coverage"] = "partial"
        self.blocked()
        self.assertEqual(evaluate(self.base)["score"], 100)

    def test_changed_source_invalidates_readiness(self):
        (self.base / "notes.txt").write_text("Outra decisão.")
        self.assertFalse(evaluate(self.base)["ready"])

    def test_critical_question_blocks(self):
        self.docs["model"]["questions"] = [{"id": "Q-001", "statement": "Quem exporta?", "severity": "high", "status": "open"}]
        self.blocked()

    def test_resolution_needs_evidence(self):
        self.docs["model"]["questions"] = [{"id": "Q-001", "statement": "Quem exporta?", "severity": "high", "status": "resolved", "resolution_evidence": []}]
        self.blocked()

    def test_missing_acceptance_blocks(self):
        self.docs["model"]["requirements"][0]["acceptance_criteria"] = []
        self.blocked()

    def test_broken_evidence_reference_blocks(self):
        self.docs["model"]["requirements"][0]["evidence"] = ["EV-missing"]
        self.blocked()

    def test_proposed_and_inferred_requirements_block(self):
        self.docs["model"]["requirements"][0]["status"] = "proposed"
        self.blocked()
        self.docs["model"]["requirements"][0]["status"] = "validated"
        self.docs["evidence"]["evidence"][0]["kind"] = "inference"
        self.blocked()

    def test_duplicate_requirement_ids_block(self):
        self.docs["model"]["requirements"] *= 2
        self.blocked()

    def test_invalid_check_and_illegal_na_block(self):
        self.docs["assessment"]["checks"]["scope"]["status"] = "not-applicable"
        self.blocked()
        self.docs["assessment"]["checks"]["scope"]["status"] = "anything"
        self.blocked()

    def test_na_normalizes_denominator(self):
        for key in ("data", "integrations"):
            self.docs["assessment"]["checks"][key]["status"] = "not-applicable"
        self.save()
        self.assertEqual(evaluate(self.base)["score"], 100)
        self.docs["assessment"]["checks"]["quality"]["status"] = "missing"
        self.docs["assessment"]["checks"]["risks"]["status"] = "missing"
        self.blocked()  # 90/95 = 94.7368, não arredonda para 95.

    def test_threshold_95_passes_without_critical_issues(self):
        for key in ("data", "integrations"):
            self.docs["assessment"]["checks"][key]["status"] = "missing"
        self.save()
        self.assertTrue(evaluate(self.base)["ready"])
        self.assertEqual(evaluate(self.base)["score"], 95)

    def test_raw_audio_needs_transcript(self):
        self.docs["sources"]["sources"][0]["kind"] = "audio"
        self.blocked()

    def test_source_exclusion_requires_reason(self):
        self.docs["sources"]["sources"][0]["required"] = False
        self.blocked()

    def test_changed_output_and_input_invalidate_seal(self):
        seal(self.base)
        (self.req / "PRD.md").write_text("Alterado REQ-001")
        with self.assertRaises(Invalid):
            delivery_hash(self.base)
        seal(self.base)
        self.docs["model"]["revision"] += 1
        self.save()
        with self.assertRaises(Invalid):
            delivery_hash(self.base)

    def test_missing_id_cannot_seal(self):
        (self.req / "PRD.md").write_text("REQ-001-extra não é REQ correto.")
        with self.assertRaises(Invalid):
            seal(self.base)

    def test_required_flag_cannot_disable_existing_package(self):
        self.assertTrue(required(self.base, {"discovery": {"required": False}}))
        self.assertFalse(required(self.base / "legacy", {}))

    def test_malformed_yaml_returns_diagnostic(self):
        (self.req / "assessment.yaml").write_text("checks: [invalid")
        self.assertFalse(evaluate(self.base)["ready"])

    def test_integration_g1_fingerprint(self):
        template = yaml.safe_load((HERE.parent / "templates/state.template.yaml").read_text())
        owner = template.pop("_schema")["owner"]
        template.update(state="refinement", ui_impact=False)
        for name in ("spec.md", "refinement.md"):
            (self.base / name).write_text("REQ-001 fixture técnica")
        # O gate exige a ordem canônica, mesmo quando o fixture é serializado.
        def save_state():
            (self.base / "state.yaml").write_text(yaml.safe_dump(template, sort_keys=False))
        def gate(dest):
            return subprocess.run(["bash", str(HERE / "gate-check.sh"), str(self.base), dest], capture_output=True, text=True)
        save_state()
        seal(self.base)
        r = gate("ready-for-dev")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        template["state"] = "ready-for-dev"
        template["gates"]["G1"].update(status="approved", approver=owner, at="2026-09-07T00:00:00Z")
        save_state()
        self.assertNotEqual(gate("in-development").returncode, 0)

        template["gates"]["G1"]["requirements_hash"] = delivery_hash(self.base)
        save_state()
        self.assertEqual(gate("in-development").returncode, 0)
        (self.base / "evidence").mkdir()
        for name in ("lint", "build", "test"):
            (self.base / "evidence" / f"{name}.log").write_text("fixture")
        template["state"] = "in-development"
        save_state()
        self.assertEqual(gate("developed").returncode, 0)
        (self.base / "spec.md").write_text("REQ-001 novo escopo")
        self.assertNotEqual(gate("in-development").returncode, 0)
        self.assertIn("discovery:", gate("developed").stdout)
        self.req.rename(self.base / "requirements-removido")
        self.assertIn("discovery:", gate("developed").stdout)

    def test_gate_set_binds_actual_revision_and_rejects_invalid_package(self):
        with tempfile.TemporaryDirectory() as sandbox:
            runtime = Path(sandbox)
            shutil.copytree(HERE.parent, runtime / "faber", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            target = runtime / "faber/tasks/TASK-000"
            shutil.copytree(self.base, target)
            template = yaml.safe_load((HERE.parent / "templates/state.template.yaml").read_text())
            owner = template.pop("_schema")["owner"]
            template.update(state="ready-for-dev", ui_impact=False)
            (target / "state.yaml").write_text(yaml.safe_dump(template, sort_keys=False))
            for name in ("spec.md", "refinement.md"):
                (target / name).write_text("REQ-001 fixture técnica")
            (runtime / "faber/config/faber.env").write_text('FABER_GH="off"\nFABER_BOARD="off"\n')
            for cmd in (["git", "init", "-q"], ["git", "config", "user.name", "Teste local"], ["git", "config", "user.email", "test@example.invalid"]):
                subprocess.run(cmd, cwd=runtime, check=True, capture_output=True)
            seal(target)
            expected = delivery_hash(target)
            command = ["bash", str(runtime / "faber/scripts/gate-set.sh"), "TASK-000", "G1", "approved", "--by", owner]
            result = subprocess.run(command, cwd=runtime, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state_path = target / "state.yaml"
            state = yaml.safe_load(state_path.read_text())
            self.assertEqual(state["gates"]["G1"]["requirements_hash"], expected)
            before = state_path.read_bytes()
            (target / "notes.txt").write_text("Decisão alterada sem revisão")
            result = subprocess.run(command, cwd=runtime, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(state_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
