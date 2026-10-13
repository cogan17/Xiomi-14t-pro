"""Focused host-only tests for the KSUN G5 candidate promotion guard."""
import unittest
from scripts.rothko_ksun_cred_candidate_guard import check


class SharedCredCandidateGuardTests(unittest.TestCase):
    def test_rejects_unguarded_global_borrow_even_with_release(self):
        patch = ("+    borrowed_cred = get_cred(ksu_cred);\n"
                 "+    put_cred(borrowed_cred);\n")
        self.assertTrue(any("lifetime guard" in p for p in check(patch)))

    def test_detects_missing_release(self):
        patch = "+    borrowed_cred = get_cred(ksu_cred);\n"
        self.assertTrue(any("fewer borrowed reference releases" in p for p in check(patch)))

    def test_does_not_require_release_without_borrow(self):
        self.assertEqual(check("+    return -EINVAL;\n"), [])

    def test_ignores_removed_unsafe_code(self):
        self.assertEqual(check("-    borrowed_cred = get_cred(ksu_cred);\n"), [])

    def test_ignores_diff_header(self):
        self.assertEqual(check("+++ b/kernel/runtime/ksud_integration.c\n"), [])


if __name__ == "__main__":
    unittest.main()
