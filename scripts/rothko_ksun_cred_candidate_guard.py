#!/usr/bin/env python3
"""Source-only guard: unsafe G5 credential borrowing must not be promoted."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'patches/rothko-ksun-g5-module-rc-borrowed-cred-candidate.patch'


def check(text: str) -> list[str]:
    problems = []
    additions = [line[1:] for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]
    if any('get_cred(ksu_cred)' in line for line in additions):
        problems.append('G5 borrows global ksu_cred without proven publication/lifetime guard')
    if not any('put_cred(borrowed_cred)' in line for line in additions):
        problems.append('G5 candidate does not show borrowed reference release')
    return problems


def main() -> int:
    problems = check(CANDIDATE.read_text())
    for problem in problems:
        print('BLOCK:', problem)
    if not problems:
        print('No known G5 borrow anti-pattern in candidate; full review still required')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
