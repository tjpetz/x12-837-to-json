"""Command-line entry point: convert an X12 837 file to JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import X12ParseError, parse_x12
from .transform import transform_document


def convert(text: str) -> dict:
    """Parse raw X12 837 text and return the equivalent JSON-serializable
    dict.
    """

    envelope = parse_x12(text)
    return transform_document(envelope)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="x12-837-to-json",
        description="Convert an X12 EDI 837 (Health Care Claim) transaction to JSON.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Path to the X12 837 file. Reads from stdin if omitted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="Where to write the JSON output. Defaults to stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for the JSON output (default: 2). Use 0 for compact output.",
    )
    args = parser.parse_args(argv)

    text = args.input.read()
    try:
        result = convert(text)
    except X12ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    indent = args.indent if args.indent > 0 else None
    json.dump(result, args.output, indent=indent)
    args.output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
