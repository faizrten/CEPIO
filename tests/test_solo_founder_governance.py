"""Regression tests for narrowly scoped solo-founder PR governance relaxation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/governance.yml"


def governance_python():
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if "python - <<'PY'" in line)
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "PY")
    code = "\n".join(line[10:] if line.startswith("          ") else line for line in lines[start + 1 : end])
    compile(code, str(WORKFLOW), "exec")
    return code


SUMMARY = "A harmless documentation change describing how to use the public interface."


def simple_body(risk="low", summary=SUMMARY, with_ip=True):
    body = "## Summary\n" + summary + "\n\n## Risk classification\n- [x] " + risk + "\n"
    if with_ip:
        body += "\n## IP / publication review\n- [x] **PUBLIC** — reviewed for publication.\n"
    return body


class SoloFounderGovernanceTests(unittest.TestCase):
    def execute(self, body, *, docs_only, title="docs: update quickstart"):
        with tempfile.TemporaryDirectory() as directory:
            event = Path(directory) / "event.json"
            event.write_text(json.dumps({"pull_request": {"body": body, "title": title}}), encoding="utf-8")
            environment = {**os.environ, "GITHUB_EVENT_PATH": str(event), "CEPIO_DOCS_ONLY": str(docs_only).lower()}
            return subprocess.run(
                [sys.executable, "-c", governance_python()],
                env=environment, capture_output=True, text=True, check=False,
            )

    def test_low_risk_verified_docs_accepts_short_form(self):
        result = self.execute(simple_body(), docs_only=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_or_unknown_files_cannot_claim_docs_short_form(self):
        result = self.execute(simple_body(), docs_only=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required PR section", result.stdout)

    def test_medium_or_high_risk_cannot_claim_short_form(self):
        for risk in ("medium", "high"):
            with self.subTest(risk=risk):
                self.assertNotEqual(self.execute(simple_body(risk=risk), docs_only=True).returncode, 0)

    def test_missing_ip_review_rejected(self):
        result = self.execute(simple_body(with_ip=False), docs_only=True)
        self.assertNotEqual(result.returncode, 0)

    def test_meaningless_summary_rejected(self):
        result = self.execute(simple_body(summary="tiny"), docs_only=True)
        self.assertNotEqual(result.returncode, 0)

    def test_wip_title_rejected(self):
        result = self.execute(simple_body(), docs_only=True, title="WIP docs")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
