#!/usr/bin/env python3
"""Backward-compatible CLI wrapper.

The implementation now lives in the modular `turmo/` package.
Existing commands like `python turmo_lite.py --help` still work.
"""

from turmo.core import *  # noqa: F401,F403 - compatibility for GUI/old scripts
from turmo.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
