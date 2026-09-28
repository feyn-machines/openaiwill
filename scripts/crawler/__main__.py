"""`python scripts/crawler <command>` — see cli.py."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Run as a directory: make `crawler` importable as a package.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from crawler.cli import main
else:
    from .cli import main

raise SystemExit(main())
