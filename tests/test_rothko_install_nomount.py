"""Synthetic NoMount source integration tests (no network, device, or kernel build)."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rothko_install_nomount import integrate, audit_baseline, PIN


class NoMountSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.tree = self.base / "kernel"
        (self.tree / "fs").mkdir(parents=True)
        (self.tree / "Makefile").write_text(
            "VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 57\n"
        )
        (self.tree / "build.config.common").write_text("KMI_GENERATION=11\n")
        (self.tree / "fs/Kconfig").write_text(
            'menu "File systems"\nsource "fs/ext4/Kconfig"\nendmenu\n'
        )
        (self.tree / "fs/Makefile").write_text("obj-y += ext4/\n")
        self.upstream = self.base / "NoMount"
        (self.upstream / "kernel/src").mkdir(parents=True)
        (self.upstream / "kernel/src/Kconfig").write_text(
            "config NOMOUNT\n\ttristate \"NoMount\"\n"
        )
        (self.upstream / "kernel/src/Makefile").write_text(
            "obj-$(CONFIG_NOMOUNT) += nomount.o\n"
        )
        (self.upstream / "kernel/src/nomount.c").write_text("int nomount_test;\n")

    def test_integrates_exactly_once(self):
        audit_baseline(self.tree)
        integrate(self.tree, self.upstream)
        self.assertTrue((self.tree / "fs/nomount/nomount.c").is_file())
        self.assertIn("obj-$(CONFIG_NOMOUNT) += nomount/",
                      (self.tree / "fs/Makefile").read_text())
        self.assertIn('source "fs/nomount/Kconfig"\nendmenu',
                      (self.tree / "fs/Kconfig").read_text())
        with self.assertRaisesRegex(ValueError, "already present"):
            integrate(self.tree, self.upstream)

    def test_rejects_wrong_baseline(self):
        (self.tree / "Makefile").write_text(
            "VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 177\n"
        )
        with self.assertRaisesRegex(ValueError, "6.1.57"):
            audit_baseline(self.tree)

    def test_rejects_invalid_source_without_modifying_fs(self):
        (self.upstream / "kernel/src/Kconfig").unlink()
        before = (self.tree / "fs/Makefile").read_text()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            integrate(self.tree, self.upstream)
        self.assertEqual((self.tree / "fs/Makefile").read_text(), before)
        self.assertFalse((self.tree / "fs/nomount").exists())

    def test_upstream_pin_immutable(self):
        self.assertEqual(len(PIN), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in PIN))


if __name__ == "__main__":
    unittest.main()
