#!/usr/bin/env python3
"""Novel related functions."""

import argparse
import json
import os
import pprint
import re
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
)
from markdown_novel_tools.convert import (
    convert_chapter,
    convert_full,
    convert_simple_pdf,
    get_output_basestr,
    single_markdown_to_pdf,
)
from markdown_novel_tools.frontmatter import fix_frontmatter, frontmatter_check
from markdown_novel_tools.mdfile import (
    get_markdown_file,
    walk_previous_revision,
    walk_repo_dir,
    write_markdown_file,
)
from markdown_novel_tools.outline import build_table_from_file, get_beats
from markdown_novel_tools.repo import commits_today, replace
from markdown_novel_tools.shunn import shunn_docx, shunn_md
from markdown_novel_tools.utils import find_markdown_files, write_to_file


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
    beats_type="outline",
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
            beats_type=beats_type,
        )
    else:
        print("No table found!", file=sys.stderr)
        sys.exit(1)


def _write_to_file_helper(path, contents, header=None):
    """Preserve existing header."""
    # TODO
    return write_to_file(path, contents)


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


def novel_lint(args):
    """Get the stats for the manuscript"""
    files = find_markdown_files(args.path)
    errors = ""
    exit_code = 0
    for path in files:
        markdown_file = get_markdown_file(path)
        is_manuscript = markdown_file.manuscript_info["is_manuscript"]
        line_num = 0
        body = ""
        for line in markdown_file.body.splitlines():
            line_num += 1
            if "[[[" in line:
                if args.fix:
                    line = re.sub(r"\[\[\[+", "[[", line)
                else:
                    errors = f"{errors}\n{path} line {line_num}: found [[["
            if is_manuscript:
                if re.match(r"^\s*-", line):
                    if args.fix:
                        continue
                    else:
                        errors = f"{errors}\n{path} line {line_num}: starts with -"
            body = f"{body}{line}\n"
        if args.fix:
            if is_manuscript:
                markdown_file.parsed_yaml = fix_frontmatter(markdown_file.parsed_yaml)
            markdown_file.body = body
            write_markdown_file(path, markdown_file)
    if not args.fix:
        exit_code = frontmatter_check(args, strict=False)
        if errors:
            print(errors)
            exit_code = 1
        sys.exit(exit_code)


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
    if "arcs" in path.name:
        print(
            f"WARNING: If {path} is an `arcs` file, you are in danger of scrambling the beat order!",
            file=sys.stderr,
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
        beats_type="arcs",
    )
    write_to_file(parent / f"{output_basestr}-arcs.html", contents)

    # Scene
    contents, stats = _beats_helper(
        path,
        column="Scene",
        multi_table_output=True,
        stats=True,
        format_="html",
        beats_type="scenes",
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

    books, stats, errors = walk_repo_dir(args.config)
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


def novel_sync(args):
    """Sync the various outline files."""
    if args.path:
        path = Path(args.path)
    else:
        path = get_primary_outline_path(args.config)

    if args.artifact_dir:
        parent = Path(args.artifact_dir)
    else:
        parent = path.parent

    if args.outline_name:
        outline_path = str(parent / args.outline_name)
    else:
        outline_path = str(parent / args.config["outline"]["outline_name"])

    parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "full": Path(outline_path.format(outline_type="full")),
        "scenes": Path(outline_path.format(outline_type="scenes")),
        "povs": Path(outline_path.format(outline_type="povs")),
        "arcs": Path(outline_path.format(outline_type="arcs")),
        "questions": Path(outline_path.format(outline_type="questions")),
    }
    # TODO hacky
    contents = stats = ""
    if "arcs" in path.name:
        print(
            f"WARNING: If {path} is an `arcs` file, you are in danger of scrambling the beat order!",
            file=sys.stderr,
        )
        contents, stats = _beats_helper(path, column="Arcs", file_headers=True, stats=True)
    elif path == paths["scenes"]:
        contents, stats = _beats_helper(path, column="Scene", file_headers=True, stats=True)
    elif path == paths["povs"]:
        contents, stats = _beats_helper(paths["full"], column="POV", file_headers=True, stats=True)
    if contents and stats:
        write_to_file(paths["full"], contents)
        print(f"{stats}\n", file=sys.stderr)
    elif not os.path.exists(paths["full"]):
        shutil.copyfile(path, paths["full"])

    # POVS
    contents, stats = _beats_helper(
        paths["full"],
        column="POV",
        file_headers=True,
        multi_table_output=True,
        stats=True,
        beats_type="povs",
    )
    write_to_file(paths["povs"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Arc
    contents, stats = _beats_helper(
        paths["full"],
        column="Arc",
        file_headers=True,
        multi_table_output=True,
        split_column=["Arc", "Beat"],
        stats=True,
        beats_type="arcs",
    )
    write_to_file(paths["arcs"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Scene
    contents, stats = _beats_helper(
        paths["full"],
        column="Scene",
        file_headers=True,
        multi_table_output=True,
        stats=True,
        beats_type="scenes",
    )
    write_to_file(paths["scenes"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Questions etc.
    contents, stats = _beats_helper(
        paths["full"],
        column="Beat",
        file_headers=True,
        filter=["Question", "Promise", "Reveal", "Goal", "SubGoal", "Death"],
        split_column=["Arc", "Beat"],
        stats=True,
        beats_type="questions",
    )
    write_to_file(paths["questions"], contents)
    print(f"{stats}\n", file=sys.stderr)


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
        "--outline-name",
        default=config["outline"]["outline_name"],
        help="The template string for each outline. Include the `{outline_type}` string.",
    )
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

    # novel lint
    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("-f", "--fix", action="store_true")
    lint_parser.add_argument("path")
    lint_parser.set_defaults(func=novel_lint)

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
