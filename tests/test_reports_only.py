import hashlib
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MUTABLE_METADATA = [
    ROOT / "metadata" / "current-version-registry.json",
    ROOT / "metadata" / "p0-core-documents.json",
    ROOT / "metadata" / "business-legal-gaps.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ReportsOnlyRegressionTests(unittest.TestCase):
    def test_reports_only_does_not_mutate_metadata(self):
        before = {p: sha256(p) for p in MUTABLE_METADATA}
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "v501_p0.py"), "--reports-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, proc.returncode, msg=proc.stdout + "\n" + proc.stderr)
        after = {p: sha256(p) for p in MUTABLE_METADATA}
        self.assertEqual(before, after)
        self.assertIn("--reports-only", proc.stdout)


if __name__ == "__main__":
    unittest.main()
