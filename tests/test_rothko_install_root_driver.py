"""Synthetic integration contract tests; never fetch upstream or compile kernel."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_symlink_failure_rolls_back_both_build_files(self):
        makefile = self.tree / "drivers/Makefile"
        kconfig = self.tree / "drivers/Kconfig"
        original_make = makefile.read_bytes()
        original_config = kconfig.read_bytes()
        with patch.object(Path, "symlink_to", side_effect=OSError("simulated link failure")):
            with self.assertRaisesRegex(OSError, "simulated link failure"):
                install(self.tree, self.driver)
        self.assertEqual(makefile.read_bytes(), original_make)
        self.assertEqual(kconfig.read_bytes(), original_config)
        self.assertFalse((self.tree / "drivers/kernelsu").exists())

    def test_rollback_failure_is_explicit_and_other_files_restored(self):
        makefile = self.tree / "drivers/Makefile"
        kconfig = self.tree / "drivers/Kconfig"
        original_config = kconfig.read_text()
        original_symlink = Path.symlink_to
        original_write = Path.write_text

        def fail_symlink(path, *args, **kwargs):
            raise OSError("simulated symlink failure")

        def fail_makefile_restore(path, text, *args, **kwargs):
            if path == makefile and text == "obj-y += base/\\n":
                raise OSError("simulated rollback failure")
            return original_write(path, text, *args, **kwargs)

        with patch.object(Path, "symlink_to", fail_symlink), patch.object(
            Path, "write_text", fail_makefile_restore
        ):
            with self.assertRaisesRegex(RuntimeError, "rollback was incomplete"):
                install(self.tree, self.driver)
        self.assertEqual(kconfig.read_text(), original_config)
        self.assertFalse((self.tree / "drivers/kernelsu").exists())

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
