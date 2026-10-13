"""Test Rothko's stage-1 no-build form and root isolation."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rothko_feature_plan import FEATURES, ROOTS, select, summary


class RothkoFormTests(unittest.TestCase):
    def setUp(self):
        self.flags = {name: "true" for name, _ in FEATURES}
        self.flags["performance"] = "false"
        self.flags["release_notes_preview"] = "false"

    def test_independent_root_matrix(self):
        for selection, expected in ROOTS.items():
            with self.subTest(selection=selection):
                variants, selected = select(selection, self.flags, "refs/heads/dev/rothko")
                self.assertEqual(variants, expected)
                self.assertTrue(selected["susfs"])
        self.assertEqual(set(ROOTS), {"KernelSU-Next", "BakaSU"})

    def test_wrong_root_branch_and_boolean_fail(self):
        with self.assertRaises(ValueError):
            select("No Root", self.flags, "refs/heads/dev/rothko")
        for archived in ("KernelSU", "All (KSU + KSUN + BakaSU)"):
            with self.assertRaisesRegex(ValueError, "archived"):
                select(archived, self.flags, "refs/heads/dev/rothko")
        with self.assertRaises(ValueError):
            select("BakaSU", self.flags, "refs/heads/bsp-rothko-u-oss")
        with self.assertRaises(ValueError):
            select("BakaSU", dict(self.flags, nomount="yes"), "refs/heads/dev/rothko")

    def test_exactly_ten_ui_fields_and_correct_defaults(self):
        form = (ROOT / ".github/workflows/Patch Kernel Features.yml").read_text()
        form = form.split("    inputs:\n", 1)[1].split("\npermissions:", 1)[0]
        fields = re.findall(r"^      ([a-z_]+):$", form, re.MULTILINE)
        self.assertEqual(fields, ["root_flavor", *[name for name, _ in FEATURES]])
        self.assertIn("default: 'BakaSU'", form)
        self.assertNotRegex(form.lower(), "droidspaces|ntsync|zram|re.kernel|cve")
        for key in ("susfs", "nomount", "baseband_guard", "networking",
                    "ptrace_patch", "unicode_fix", "bpf_stack"):
            block = re.search(rf"(?m)^      {key}:\n((?:^        .*\n)+)", form).group(1)
            self.assertIn("default: true", block)
        for key in ("performance", "release_notes_preview"):
            block = re.search(rf"(?m)^      {key}:\n((?:^        .*\n)+)", form).group(1)
            self.assertIn("default: false", block)

    def test_cli_writes_expected_no_build_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROOT_FLAVOR="KernelSU-Next",
                       GITHUB_REF="refs/heads/dev/rothko",
                       GITHUB_OUTPUT=str(Path(tmp) / "out"),
                       GITHUB_STEP_SUMMARY=str(Path(tmp) / "summary"))
            env.update({name.upper(): value for name, value in self.flags.items()})
            run = subprocess.run([sys.executable, str(ROOT / "scripts/rothko_feature_plan.py")],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('root_matrix=["KernelSU-Next"]',
                          Path(tmp, "out").read_text())
            self.assertIn("PLAN ONLY", Path(tmp, "summary").read_text())
        opts = {name: raw == "true" for name, raw in self.flags.items()}
        opts["release_notes_preview"] = True
        self.assertIn("root-variant jobs are skipped", summary("BakaSU", ["BakaSU"], opts))


if __name__ == "__main__":
    unittest.main()
