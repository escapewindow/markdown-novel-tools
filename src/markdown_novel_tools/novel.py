#!/usr/bin/env python3
"""Novel related functions."""

import argparse
import json
import os
import pprint
import shutil
import sys
from pathlib import Path

from git import Repo

from markdown_novel_tools.config import (
    add_config_parser_args,
    get_config,
    get_css_path,
    get_markdown_template_choices,
    get_primary_outline_path,
    get_valid_primary_outline_filenames,
)
from markdown_novel_tools.convert import (
    convert_chapter,
    convert_full,
    convert_simple_pdf,
    get_output_basestr,
    single_markdown_to_pdf,
)
from markdown_novel_tools.mdfile import walk_previous_revision, walk_repo_dir
from markdown_novel_tools.outline import build_table_from_file, get_beats
from markdown_novel_tools.repo import commits_today, replace
from markdown_novel_tools.shunn import shunn_docx, shunn_md
from markdown_novel_tools.utils import write_to_file


def _beats_helper(
    path,
    column=None,
    filter=None,
    file_headers=False,
    multi_table_output=False,
    order=None,
    split_column=None,
    stats=False,
    target_table_num=None,
    format_=None,
):
    """Shared logic from novel_beats and novel_sync"""
    table = build_table_from_file(
        path,
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
            format_=format_,
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
        print("Specify column with `--column` when filtering!", file=sys.stderr)
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
        format_=args.format,
    )
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr)


def novel_sync(args):
    """Sync the various outline files."""
    if args.path:
        path = Path(args.path)
    else:
        path = get_primary_outline_path(args.config)

    valid_primary_outline_filenames = get_valid_primary_outline_filenames(args.config)
    if path.name not in valid_primary_outline_filenames:
        raise Exception(
            f"{path} is not in {valid_primary_outline_filenames}; quitting before we break beat order."
        )

    if args.artifact_dir:
        parent = Path(args.artifact_dir)
    else:
        parent = path.parent

    parent.mkdir(parents=True, exist_ok=True)
    full_path = parent / f"book{args.config['book_num']}-full.md"
    if path.name == f"book{args.config['book_num']}-scenes.md":
        contents, stats = _beats_helper(path, column="Scene", file_headers=True, stats=True)
        write_to_file(full_path, contents)
        print(f"{stats}\n", file=sys.stderr)
    elif not os.path.exists(full_path):
        shutil.copyfile(path, full_path)

    # POVS
    contents, stats = _beats_helper(
        full_path, column="POV", file_headers=True, multi_table_output=True, stats=True
    )
    write_to_file(parent / f"book{args.config['book_num']}-povs.md", contents)
    print(f"{stats}\n", file=sys.stderr)

    # Arc
    contents, stats = _beats_helper(
        full_path,
        column="Arc",
        file_headers=True,
        multi_table_output=True,
        split_column=["Arc", "Beat"],
        stats=True,
    )
    write_to_file(parent / f"book{args.config['book_num']}-arcs.md", contents)
    print(f"{stats}\n", file=sys.stderr)

    # Scene
    contents, stats = _beats_helper(
        full_path, column="Scene", file_headers=True, multi_table_output=True, stats=True
    )
    write_to_file(parent / f"book{args.config['book_num']}-scenes.md", contents)
    print(f"{stats}\n", file=sys.stderr)

    # Questions etc.
    contents, stats = _beats_helper(
        full_path,
        column="Beat",
        file_headers=True,
        filter=["Question", "Promise", "Reveal", "Goal", "SubGoal", "Death"],
        split_column=["Arc", "Beat"],
        stats=True,
    )
    write_to_file(parent / f"book{args.config['book_num']}-questions.md", contents)
    print(f"{stats}\n", file=sys.stderr)


def novel_convert(args):
    """Convert a novel to a different file format."""
    if args.format in ("pdf", "epub", "chapter-pdf", "shunn-docx", "shunn-md", "simple-pdf"):
        if not shutil.which("pandoc"):
            print(f"`{args.format}` format requires `pandoc`! Exiting...", file=sys.stderr)
            sys.exit(1)
    if args.format == "epub":
        if not shutil.which("magick"):
            print(f"`{args.format}` format requires `imagemagick`! Exiting...", file=sys.stderr)
            sys.exit(1)
    if args.format == "chapter-pdf":
        convert_chapter(args, per_chapter_callback=single_markdown_to_pdf)
    elif args.format == "shunn-docx":
        shunn_docx(args)
    elif args.format == "shunn-md":
        shunn_md(args)
    elif args.format == "simple-pdf":
        convert_simple_pdf(args)
    else:
        convert_full(args)


def novel_new(args):
    """Create a new file from template."""

    path = Path(args.path)
    template = Path(args.config["markdown_template_dir"]) / f"{args.template}.md"
    if args.create_missing_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy(template, path)


def novel_outline_convert(args):
    """Convert the outline to something shareable."""
    path = get_primary_outline_path(args.config)
    valid_primary_outline_filenames = get_valid_primary_outline_filenames(args.config)
    if path.name not in valid_primary_outline_filenames:
        raise Exception(
            f"{path} is not in {valid_primary_outline_filenames}; quitting before we break beat order."
        )

    output_basestr = get_output_basestr(args)

    if args.artifact_dir:
        parent = Path(args.artifact_dir)
        if args.clean and os.path.exists(args.artifact_dir):
            shutil.rmtree(args.artifact_dir)
    else:
        parent = path.parent

    parent.mkdir(parents=True, exist_ok=True)

    # Arc
    contents, stats = _beats_helper(
        path,
        column="Arc",
        multi_table_output=True,
        split_column=["Arc", "Beat"],
        stats=True,
        format_="html",
    )
    write_to_file(parent / f"{output_basestr}-arcs.html", contents)

    # Scene
    contents, stats = _beats_helper(
        path, column="Scene", multi_table_output=True, stats=True, format_="html"
    )
    write_to_file(parent / f"{output_basestr}-scenes.html", contents)

    if args.format == "pdf":
        for base_name in (f"{output_basestr}-arcs", f"{output_basestr}-scenes"):
            single_markdown_to_pdf(
                args,
                base_name,
                parent / f"{base_name}.html",
                artifact_dir=parent,
                css_path=get_css_path(args.config, variant="misc_pdf_css_path"),
            )


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
    commits = commits_today(args.config)

    print(f"""{"\n".join(commits[::-1])}""")
    print(f"""{len(commits)} commits today.""")


def novel_parser():
    """Return a parser for the novel tool."""
    config, remaining_args = get_config()
    parser = argparse.ArgumentParser(prog="novel")
    add_config_parser_args(
        parser
    )  # these args will be swallowed by the config_parser, but add for --help
    parser.set_defaults(config=config)
    parser.add_argument("-v", "--verbose", help="Verbose logging.", action="store_true")
    subparsers = parser.add_subparsers()

    # novel beats
    beats_parser = subparsers.add_parser("beats")
    beats_parser.set_defaults(require_book_num=True)
    beats_parser.add_argument(
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
        "--format",
        choices=["yaml", "markdown", "html"],
        default="markdown",
        help="Markdown table, yaml header, or html table mode.",
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

    sync_parser = subparsers.add_parser("sync", help="Sync the various outline files.")
    sync_parser.set_defaults(require_book_num=True)
    sync_parser.add_argument("--artifact-dir", help="Defaults to the parent of PATH")
    sync_parser.add_argument(
        "path", nargs="?", help="Defaults to the config or default primary outline path."
    )
    sync_parser.set_defaults(func=novel_sync)

    # novel convert
    convert_parser = subparsers.add_parser("convert")
    convert_parser.set_defaults(require_book_num=True)
    convert_parser.add_argument(
        "--format",
        choices=("pdf", "chapter-pdf", "shunn-docx", "shunn-md", "text", "epub", "simple-pdf"),
        default="text",
    )
    convert_parser.add_argument("--subtitle", default="")
    convert_parser.add_argument("--clean", action="store_true")
    convert_parser.add_argument("--artifact-dir", default="_output")
    convert_parser.add_argument("filename", nargs="+")
    convert_parser.set_defaults(func=novel_convert)

    # novel new
    new_parser = subparsers.add_parser("new")
    new_parser.add_argument(
        "-p",
        "--create-missing-parents",
        action="store_true",
        help="Like `mkdir -p`; create the missing directory structure if needed.",
    )
    new_parser.add_argument("template", choices=get_markdown_template_choices(config))
    new_parser.add_argument("path")
    new_parser.set_defaults(func=novel_new)

    # novel outline-convert
    outline_convert_parser = subparsers.add_parser("outline_convert")
    outline_convert_parser.set_defaults(require_book_num=True)
    outline_convert_parser.add_argument(
        "--format",
        choices=("pdf", "html"),
        default="html",
    )
    outline_convert_parser.add_argument("--subtitle", default="")
    outline_convert_parser.add_argument("--clean", action="store_true")
    outline_convert_parser.add_argument("--artifact-dir", default="_output")
    outline_convert_parser.set_defaults(func=novel_outline_convert)

    # novel replace
    replace_parser = subparsers.add_parser("replace")
    replace_parser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    replace_parser.add_argument("from_")
    replace_parser.add_argument("to")
    replace_parser.set_defaults(func=replace)

    # novel stats
    stats_parser = subparsers.add_parser("stats")
    stats_parser.set_defaults(require_book_num=True)
    stats_parser.set_defaults(func=novel_stats)

    # novel today
    today_parser = subparsers.add_parser("today")
    today_parser.set_defaults(func=novel_today)

    return parser, remaining_args


def novel_tool():
    """Work on the outline, repo, and manuscript."""

    parser, remaining_args = novel_parser()
    args = parser.parse_args(remaining_args)
    if (
        hasattr(args, "require_book_num")
        and args.require_book_num
        and args.config.get("book_num") is None
    ):
        print(f"{sys.argv}: specify -b <Book Num>!")
        raise SystemExit(1)
    if not hasattr(args, "func"):
        print(parser.format_help())
        raise SystemExit(1)
    args.func(args)
