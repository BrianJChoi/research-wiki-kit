# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pymupdf>=1.24"]
# ///
"""스크립트 회귀 시험을 모두 돌린다.

사용법:
    uv run tests/run.py

RapidOCR 시험은 모델을 내려받으므로 RWK_TEST_RAPIDOCR=1일 때만 돈다.
"""

import sys
import unittest
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
