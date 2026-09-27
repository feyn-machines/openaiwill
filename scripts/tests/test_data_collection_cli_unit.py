"""Exercise the public collection CLI without credentials or network access."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/collect-official-x.py"


class CollectionCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "data").mkdir(exist_ok=True)

    def test_plan_has_each_enabled_account_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data") as directory:
            output = Path(directory) / "run.json"
            command = [sys.executable, str(CLI), "--start", "2026-09-10T00:00:00Z", "--end", "2026-09-11T00:00:00Z", "--plan-only", "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            plan = json.loads(output.read_text())
            accounts = json.loads((ROOT / "datasets/official-x-accounts.json").read_text())
            self.assertEqual({q["handle"] for q in plan["queries"]}, {a["handle"] for a in accounts if a["enabled"]})
            self.assertEqual({q["mode"] for q in plan["queries"]}, {"user_timeline"})
            self.assertEqual(len(plan["queries"]), sum(a["enabled"] for a in accounts))
            self.assertEqual(plan["status"], "planned")
            self.assertFalse(plan["ok"])
            before = output.read_bytes()
            again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), before)

    def test_output_outside_private_data_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            result = subprocess.run([sys.executable, str(CLI), "--start", "2026-09-10T00:00:00Z", "--end", "2026-09-11T00:00:00Z", "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_pnpm_argument_separator_is_accepted(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data") as directory:
            output = Path(directory) / "plan.json"
            result = subprocess.run([sys.executable, str(CLI), "--", "--start", "2026-09-10T00:00:00Z", "--end", "2026-09-11T00:00:00Z", "--plan-only", "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["status"], "planned")

    def test_nonfinite_budget_is_rejected_before_reserving_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data") as directory:
            output = Path(directory) / "plan.json"
            result = subprocess.run(
                [sys.executable, str(CLI), "--start", "2026-09-10T00:00:00Z",
                 "--end", "2026-09-11T00:00:00Z", "--pace", "nan",
                 "--plan-only", "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
