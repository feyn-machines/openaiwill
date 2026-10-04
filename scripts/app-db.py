#!/usr/bin/env python3
"""Command line for schema app: setup-local now; pull is added with the submissions import."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_db


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup-local", help="create role oaw_app and schema app in the local database")
    args = parser.parse_args(argv)
    try:
        if args.command == "setup-local":
            app_db.setup_local()
    except (app_db.AppError, RuntimeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # psycopg errors never carry the password; keep one line
        print(f"error: {type(error).__name__}: {str(error).splitlines()[0] if str(error) else ''}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
