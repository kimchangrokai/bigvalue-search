"""Allow running as `python -m bigvalue_search`."""

from __future__ import annotations

import sys

from bigvalue_search.cli import main

if __name__ == "__main__":
    sys.exit(main())
