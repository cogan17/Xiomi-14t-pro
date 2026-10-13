"""Synthetic integration contract tests; never fetch upstream or compile kernel."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rothko_install_root_driver import install, verify_baseline, ROOT_REVISIONS


class RootDriverIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tree = self.root / "kernel"
        (self.tree / "drivers").mkdir(parents=True)
        (self.tree / "drivers" / "Makefile").write_text("obj-y += base/\n")
        (self.tree / "drivers" / "Kconfig").write_text(
            'menu "Device Drivers"\nsource "drivers/base/Kconfig"\nendmenu\n'
        )
        (self.tree / "Makefile").write_text(
            "VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 57\n"
        )
        (self.tree / "build.config.common").write_text("KMI_GENERATION=11\n")
        self.driver = self.root / "BakaSU"
        (self.driver / "kernel").mkdir(parents=True)
        (self.driver / "kernel/Kconfig").write_text("menu root\nconfig KSU\n\tbool\nendmenu\n")
        (self.driver / "kernel/Makefile").write_text("obj-y += core_hook.o\n")

    def test_root_flavors_exact_and_distinct(self):
        self.assertEqual(set(ROOT_REVISIONS), {"KernelSU-Next", "BakaSU"})
        self.assertEqual(len({repo for repo, sha in ROOT_REVISIONS.values()}), 2)
        self.assertTrue(all(len(sha) == 40 for repo, sha in ROOT_REVISIONS.values()))
        self.assertNotIn("KernelSU", ROOT_REVISIONS)

    def test_integrate_one_and_refuse_duplicate(self):
        verify_baseline(self.tree)
        install(self.tree, self.driver)
        self.assertTrue((self.tree / "drivers/kernelsu/Kconfig").is_file())
        self.assertIn("obj-$(CONFIG_KSU) += kernelsu/",
                      (self.tree / "drivers/Makefile").read_text())
        kconfig = (self.tree / "drivers/Kconfig").read_text()
        self.assertIn('source "drivers/kernelsu/Kconfig"\nendmenu', kconfig)
        with self.assertRaisesRegex(ValueError, "already present"):
            install(self.tree, self.driver)

    def test_refuse_unrecognized_kernel_baseline(self):
        (self.tree / "Makefile").write_text("VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 177\n")
        with self.assertRaisesRegex(ValueError, "6.1.57"):
            verify_baseline(self.tree)

    def test_refuse_incomplete_driver_without_modifying_source(self):
        (self.driver / "kernel/Kconfig").unlink()
        old = (self.tree / "drivers/Makefile").read_text()
        with self.assertRaisesRegex(ValueError, "Missing root"):
            install(self.tree, self.driver)
        self.assertEqual((self.tree / "drivers/Makefile").read_text(), old)
        self.assertFalse((self.tree / "drivers/kernelsu").exists())


if __name__ == "__main__":
    unittest.main()
