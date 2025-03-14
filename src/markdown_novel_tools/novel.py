#!/usr/bin/env python3
"""Novel related functions."""

import argparse
import json
import os
import sys
from pathlib import Path

from markdown_novel_tools.outline import parse_beats
from markdown_novel_tools.repo import num_commits_today
from markdown_novel_tools.scene import walk_current_dir, walk_previous_revision


def novel_beats(args):
    """Munge novel args, then call parse_beats."""
    if args.order:
        args.order = args.order.split(",")
    if args.split_column:
        args.split_column = args.split_column.split(",")
        if args.order:
            print("--split-column and --order are incompatible!", file=sys.stderr)
            sys.exit(1)
    if args.filter is not None and args.column is None:
        print("Specify column with `-c` when filtering!", file=sys.stderr)
        sys.exit(1)
    parse_beats(args)


def novel_convert(args):
    """Convert a novel to a different file format."""
    pass


def novel_replace(args):
    """Replace a string in files and filenames in the current directory."""
    pass


def novel_stats(args):
    """Get the stats for the manuscript"""
    artifact_dir = Path("_output")
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)

    books, stats, errors = walk_current_dir()
    for i, book in books.items():
        book_stats = book.stats()
        path = artifact_dir / f"book{i}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(book_stats, fh, indent=4)
        print(json.dumps(book_stats, indent=4))

    summary = f"""Manuscript markdown files: {stats['manuscript']['files']}
Manuscript words: {stats['manuscript']['words']}
Total markdown files: {stats['total']['files']}
Total words: {stats['total']['words']}

{walk_previous_revision(stats)}"""
    print(summary)
    with open(artifact_dir / "summary.txt", "w", encoding="utf-8") as fh:
        print(summary, file=fh)

    if errors:
        print(f"Bustage in one or more files!\n{errors}")
        sys.exit(len(errors))


def novel_today(args):
    """Get daily stats."""
    num_commits = num_commits_today()

    print(f"{num_commits} commits today.")


def novel_parser():
    """Return a parser for the novel tool."""
    parser = argparse.ArgumentParser(prog="novel")
    parser.add_argument("-v", "--verbose", help="Verbose logging.")
    subparsers = parser.add_subparsers()

    # novel beats
    beats_parser = subparsers.add_parser("beats")
    beats_parser.add_argument(
        "-c",
        "--column",
        help="Which column to sort by, if any. First column is 0, 2nd is 1, etc.",
    )
    beats_parser.add_argument(
        "-f",
        "--filter",
        nargs="+",
        help="Only print the lines where the column matches this value.",
    )
    beats_parser.add_argument(
        "-o",
        "--order",
        help="Rearrange the columns. Value is comma delimited, e.g. Arc,Description,Scene,POV",
    )
    beats_parser.add_argument(
        "-t",
        "--table",
        type=int,
        help="Specify which table number, starting from 1, to parse. Default: parse all the tables.",
    )
    beats_parser.add_argument(
        "-s", "--stats", action="store_true", help="Display stats at the end."
    )
    beats_parser.add_argument(
        "-y",
        "--yaml",
        action="store_true",
        help="Print in yaml header mode, rather than markdown table.",
    )
    beats_parser.add_argument("--split-column", help="Split column by commas.")
    beats_parser.add_argument(
        "--file-headers",
        "--fh",
        action="store_true",
        help="Print yaml headers at the start of the output.",
    )
    beats_parser.add_argument(
        "--multi-table-output",
        "-m",
        action="store_true",
        help="When sorting by column, split each value into its own table.",
    )
    beats_parser.add_argument("path")
    beats_parser.set_defaults(func=novel_beats)

    # novel convert
    convert_parser = subparsers.add_parser("convert")
    convert_parser.add_argument(
        "-o", "--outline", default="outline/Book 1 outline/scenes.md"
    )  # TODO unhardcode
    convert_parser.add_argument("path", nargs="+")
    convert_parser.set_defaults(func=novel_convert)

    # novel replace
    replace_parser = subparsers.add_parser("replace")
    replace_parser.add_argument("-f", "--field")
    replace_parser.add_argument("path", nargs="+")
    replace_parser.set_defaults(func=novel_replace)

    # novel stats
    stats_parser = subparsers.add_parser("stats")
    stats_parser.set_defaults(func=novel_stats)

    # novel today
    today_parser = subparsers.add_parser("today")
    today_parser.set_defaults(func=novel_today)

    return parser


def novel_tool():
    """Work on the outline, repo, and manuscript."""

    parser = novel_parser()
    args = parser.parse_args()
    args.func(args)
