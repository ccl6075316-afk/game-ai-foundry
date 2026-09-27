"""Repository-root launcher for the gamefactory CLI."""

from __future__ import annotations

import sys
from pathlib import Path


CLI_DIR = Path(__file__).resolve().parent / "cli"
sys.path.insert(0, str(CLI_DIR))

from gamefactory import cli  # noqa: E402


if __name__ == "__main__":
    cli()
