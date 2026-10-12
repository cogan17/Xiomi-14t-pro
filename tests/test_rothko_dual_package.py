"""Synthetic tests for Rothko dual-file candidate generation; never flash."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rothko_dual_package import (validate_image, package_ak3, sha256,
                                  repack_and_verify, AK3_SCRIPT)


class RothkoDualOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.image = self.base / "Image"
        self.stock = self.base / "stock_boot.img"
        kernel = bytearray(b'\0' * (1024 * 1024 + 128))
        kernel[0x38:0x3c] = b'ARM\x64'
        self.image.write_bytes(kernel)
        self.stock.write_bytes(b'ANDROID!' + b'\0' * (1024 * 1024))
        self.ak3 = self.base / "ak3"
        (self.ak3 / "tools").mkdir(parents=True)
        (self.ak3 / "tools/ak3-core.sh").write_text("# mock testing only\n")
        updater = self.ak3 / "META-INF/com/google/android/update-binary"
        updater.parent.mkdir(parents=True)
        updater.write_text("# mock update-binary\n")

    def test_image_validation(self):
        validate_image(self.image, kernel=True)
        validate_image(self.stock, kernel=False)
        with self.assertRaises(ValueError):
            validate_image(self.stock, kernel=True)
        with self.assertRaises(ValueError):
            validate_image(self.image, kernel=False)

    def test_ak3_package_has_hard_abort(self):
        archive = self.base / "candidate.zip"
        package_ak3(self.ak3, self.image, archive)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.testzip(), None)
            self.assertEqual(sha256(self.image),
                             __import__('hashlib').sha256(z.read("Image")).hexdigest())
            self.assertIn('abort "Rothko candidate only', z.read("anykernel.sh").decode())
            self.assertIn("device.name1=rothko", z.read("anykernel.sh").decode())
            self.assertIn("do.devicecheck=1", z.read("anykernel.sh").decode())
            self.assertNotIn("flash_boot\n", z.read("anykernel.sh").decode().split("\n# After")[0])
            self.assertIn("UNAPPROVED-CANDIDATE.txt", z.namelist())

    def test_repack_proves_embedded_kernel_matches_ak3_image(self):
        fake = self.base / "fake_magiskboot"
        fake.write_text("""#!/usr/bin/env python3
import pathlib, sys
p = pathlib.Path
action, source = sys.argv[1:3]
if action == "unpack":
    p("kernel").write_bytes(p(source).read_bytes()[8:])
elif action == "repack":
    p("new-boot.img").write_bytes(b"ANDROID!" + p("kernel").read_bytes())
else:
    raise SystemExit(1)
""")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        result = self.base / "boot.img"
        repack_and_verify(fake, self.stock, self.image, result)
        self.assertEqual(result.read_bytes()[8:], self.image.read_bytes())
        validate_image(result, kernel=False)

    def test_cli_rejects_bad_firmware_and_stale_output(self):
        output = self.base / "candidate"
        output.mkdir()
        cmd = [sys.executable, str(ROOT / "scripts/rothko_dual_package.py"),
               "--kernel-image", str(self.image), "--stock-boot", str(self.stock),
               "--magiskboot", str(self.image), "--ak3-template", str(self.ak3),
               "--root", "BakaSU", "--source-commit", "a" * 40,
               "--output", str(output)]
        rejected = subprocess.run(cmd + ["--firmware", "OS3.0.301.0.WNEIDXM"],
                                  capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        rejected2 = subprocess.run(cmd + ["--firmware", "OS3.0.301.0.WNNIDXM"],
                                   capture_output=True, text=True)
        self.assertNotEqual(rejected2.returncode, 0)


if __name__ == "__main__":
    unittest.main()
