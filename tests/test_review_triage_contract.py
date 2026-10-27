"""Static and executable contract checks for the trusted-base PR risk triage."""

from pathlib import Path
import shutil
import subprocess
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/review-triage.yml"


def js_body():
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("          script: |\n") + len("          script: |\n")
    content = text[start:].splitlines()
    return (
        "\n".join(line[12:] if line.startswith("            ") else line for line in content) + "\n"
    )


class ReviewTriageContracts(unittest.TestCase):
    def test_trusted_base_read_only_contract(self):
        yaml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", yaml)
        self.assertIn("contents: read", yaml)
        self.assertIn("pull-requests: read", yaml)
        self.assertNotIn("pull-requests: write", yaml)
        self.assertNotIn("id-token: write", yaml)
        self.assertNotIn("actions/checkout@", yaml)
        self.assertNotIn("github.rest.pulls.merge", yaml)
        self.assertNotIn("github.rest.pulls.update", yaml)
        self.assertIn("f.previous_filename", yaml)
        self.assertIn("f.status === 'removed'", yaml)

    def test_risk_classifier_javascript_syntax(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js not installed in this local runner")
        result = subprocess.run(
            [node, "--check", "-"],
            input="(async () => {\n" + js_body() + "})();\n",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
