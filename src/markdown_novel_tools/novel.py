#!/usr/bin/env python3
"""Novel related functions."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from git import Repo

from markdown_novel_tools.config import get_config, get_primary_outline_path
from markdown_novel_tools.convert import convert_chapter, convert_full
from markdown_novel_tools.outline import build_table_from_file, get_beats
from markdown_novel_tools.repo import num_commits_today, replace
from markdown_novel_tools.scene import walk_previous_revision, walk_repo_dir
from markdown_novel_tools.utils import write_to_file


def _beats_helper(
    path,
    column=None,
    filter=None,
    file_headers=False,
    multi_table_output=False,
    order=None,
    split_column=False,
    stats=False,
    target_table_num=None,
    yaml=False,
):
    """Shared logic from novel_beats and novel_sync"""
    with open(path, encoding="utf-8") as fh:
        table = build_table_from_file(
            fh,
            column=column,
            order=order,
            split_column=split_column,
            target_table_num=target_table_num,
        )

    if table:
        return get_beats(
            table,
            filter=filter,
            file_headers=file_headers,
            multi_table_output=multi_table_output,
            stats=stats,
            yaml=yaml,
        )
    else:
        print("No table found!", file=sys.stderr)
        sys.exit(1)


def novel_beats(args):
    """Print an outline's beats in the desired form."""
    if not args.path:
        args.path = get_primary_outline_path(args.config)

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

    stdout, stderr = _beats_helper(
        args.path,
        column=args.column,
        filter=args.filter,
        file_headers=args.file_headers,
        multi_table_output=args.multi_table_output,
        order=args.order,
        split_column=args.split_column,
        stats=args.stats,
        target_table_num=args.table,
        yaml=args.yaml,
    )
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr)


def novel_sync(args):
    pass


#    novel beats -c Scene --fh -s "$OUTLINE_DIR/scenes.md" > "$OUTLINE_DIR/full.md"
#
#    novel beats -c POV --fh -m -s outline/Book\ 1\ outline/full.md > outline/Book\ 1\ outline/povs.md
#    novel beats -c Arc --fh -m -s --split-column Arc,Beat outline/Book\ 1\ outline/full.md > outline/Book\ 1\ outline/arcs.md
#    novel beats -c Scene --fh -m -s outline/Book\ 1\ outline/full.md > outline/Book\ 1\ outline/scenes.md
#    novel beats -c Beat --fh -s -f Question Promise Reveal Goal SubGoal Death --split-column Arc,Beat outline/Book\ 1\ outline/full.md > outline/Book\ 1\ outline/questions.md


def novel_convert(args):
    """Convert a novel to a different file format."""
    if args.format in ("pdf", "epub", "docx", "odt", "chapter-pdf", "chapter-docx"):
        if not shutil.which("pandoc"):
            print(f"`{args.format}` format requires `pandoc`! Exiting...", file=sys.stderr)
            sys.exit(1)
    if args.format == "epub":
        if not shutil.which("magick"):
            print(f"`{args.format}` format requires `imagemagick`! Exiting...", file=sys.stderr)
            sys.exit(1)
    if args.format in ("chapter-pdf", "chapter-docx"):
        convert_chapter(args)
    else:
        convert_full(args)


def novel_stats(args):
    """Get the stats for the manuscript"""
    # pylint: disable=unused-argument
    artifact_dir = Path("_output")
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)

    books, stats, errors = walk_repo_dir()
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

{walk_previous_revision(args.config, stats)}"""
    print(summary)
    with open(artifact_dir / "summary.txt", "w", encoding="utf-8") as fh:
        print(summary, file=fh)

    if errors:
        print(f"Bustage in one or more files!\n{errors}")
        sys.exit(len(errors))


def novel_today(args):
    """Get daily stats."""
    # pylint: disable=unused-argument
    num_commits = num_commits_today(args.config)

    print(f"{num_commits} commits today.")


def novel_parser():
    """Return a parser for the novel tool."""
    config = get_config()
    parser = argparse.ArgumentParser(prog="novel")
    parser.add_argument("-v", "--verbose", help="Verbose logging.")
    parser.add_argument("-b", "--book", default="1", help="Specify the book number.")
    parser.set_defaults(config=config)
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
    beats_parser.add_argument("path", nargs="?")
    beats_parser.set_defaults(func=novel_beats)

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("path", nargs="?")
    sync_parser.set_defaults(func=novel_sync)

    # novel convert
    convert_parser = subparsers.add_parser("convert")
    convert_parser.add_argument(
        "--format",
        choices=("pdf", "chapter-pdf", "chapter-docx", "text", "epub", "docx", "odt"),
        default="text",
    )
    convert_parser.add_argument("--subtitle")
    convert_parser.add_argument("--clean", action="store_true")
    convert_parser.add_argument("--artifact-dir", default="_output")
    convert_parser.add_argument("filename", nargs="+")
    convert_parser.set_defaults(func=novel_convert)

    # novel replace
    replace_parser = subparsers.add_parser("replace")
    replace_parser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    replace_parser.add_argument("from_")
    replace_parser.add_argument("to")
    replace_parser.set_defaults(func=replace)

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
