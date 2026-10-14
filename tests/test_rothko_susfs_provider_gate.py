"""Synthetic read-only provider selection tests; no network, Actions or kernel build."""
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rothko_susfs_provider_gate as gate


class TestSusfsProviderGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.provider = self.root / "provider"
        self.bsp = self.root / "bsp"
        for path in ("kernel/feature",):
            (self.provider / path).mkdir(parents=True)
        self.bsp.mkdir()
        self.write_provider("kernel/Kconfig", "config KSU_SUSFS\n\tbool\n\tdepends on KSU\n\tdepends on THREAD_INFO_IN_TASK\n")
        self.write_provider("kernel/Kbuild", "kernelsu-objs += feature/sucompat.o\nobj-$(CONFIG_KSU) += kernelsu.o\n")
        signature = "int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags)"
        self.write_provider("kernel/feature/sucompat.h", "#ifdef CONFIG_KSU_SUSFS\n" + signature + ";\n#endif\n")
        self.write_provider("kernel/feature/sucompat.c", "#ifdef CONFIG_KSU_SUSFS\n" + signature + " { return 0; }\n#endif\n")
        (self.bsp / "Makefile").write_text("VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 57\n")
        (self.bsp / "build.config.common").write_text("KMI_GENERATION=11\n")
        self.sha = gate.PROVIDER_SHA
        self.remote = gate.PROVIDER_REMOTE
        self.git = patch.object(gate, "git_value", side_effect=self.fake_git)
        self.git.start()
        self.addCleanup(self.git.stop)

    def write_provider(self, name, data):
        p = self.provider / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data)

    def fake_git(self, directory, *args):
        return self.sha if args == ("rev-parse", "HEAD") else self.remote

    def test_matching_provider_still_cannot_install(self):
        result = gate.inspect(self.provider, self.bsp)
        self.assertEqual(result["provider_source_contract"], "verified")
        self.assertFalse(result["integration_ready"])
        self.assertEqual(set(result["missing_susfs_bsp_files"]), set(gate.BSP_REQUIRED))
        self.assertIn(gate.SESSION_BLOCKER, result["blocking_gates"])
        self.assertFalse((self.bsp / "drivers/kernelsu").exists())

    def test_vanilla_revision_rejected(self):
        self.sha = gate.VANILLA_SHA
        with self.assertRaisesRegex(gate.GateError, "Vanilla"):
            gate.inspect(self.provider, self.bsp)

    def test_wrong_sha_and_origin_rejected(self):
        self.sha = "0" * 40
        with self.assertRaisesRegex(gate.GateError, "SHA mismatch"):
            gate.inspect(self.provider, self.bsp)
        self.sha = gate.PROVIDER_SHA
        self.remote = "https://github.com/KernelSU-Next/KernelSU-Next"
        with self.assertRaisesRegex(gate.GateError, "remote mismatch"):
            gate.inspect(self.provider, self.bsp)

    def test_missing_provider_object_rejected(self):
        self.write_provider("kernel/Kbuild", "obj-$(CONFIG_KSU) += kernelsu.o\n")
        with self.assertRaisesRegex(gate.GateError, "provider object"):
            gate.inspect(self.provider, self.bsp)

    def test_mismatched_signature_rejected(self):
        p = self.provider / "kernel/feature/sucompat.c"
        p.write_text(p.read_text().replace("int *flags)", "long *flags)"))
        with self.assertRaisesRegex(gate.GateError, "definition missing"):
            gate.inspect(self.provider, self.bsp)

    def test_lost_kconfig_dependency_rejected(self):
        self.write_provider("kernel/Kconfig", "config KSU_SUSFS\n\tbool\n\tdepends on KSU\n")
        with self.assertRaisesRegex(gate.GateError, "dependencies"):
            gate.inspect(self.provider, self.bsp)

    def test_wrong_bsp_metadata_rejected(self):
        (self.bsp / "Makefile").write_text("VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 66\n")
        with self.assertRaisesRegex(gate.GateError, "6.1.57"):
            gate.inspect(self.provider, self.bsp)

    def test_missing_or_linked_source_rejected(self):
        p = self.provider / "kernel/feature/sucompat.h"
        p.unlink()
        with self.assertRaisesRegex(gate.GateError, "Missing/linked"):
            gate.inspect(self.provider, self.bsp)

    def test_complete_manifest_cannot_bypass_build_hold(self):
        for name in gate.BSP_REQUIRED:
            p = self.bsp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("/* fixture only */\n")
        result = gate.inspect(self.provider, self.bsp)
        self.assertEqual(result["missing_susfs_bsp_files"], [])
        self.assertFalse(result["integration_ready"])
        self.assertEqual(len(result["blocking_gates"]), 3)


if __name__ == "__main__":
    unittest.main()
