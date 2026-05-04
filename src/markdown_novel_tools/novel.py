#!/usr/bin/env python3
"""Novel related functions."""

import argparse
import json
import os
import pprint
import re
import shutil
import sys
from copy import deepcopy
from glob import glob
from pathlib import Path

from git import Repo

from markdown_novel_tools.config import (
    add_config_parser_args,
    get_config,
    get_css_path,
    get_markdown_template_choices,
    get_new_config_val,
)
from markdown_novel_tools.constants import BEATS_REGEX, LINKS_REGEX, QUESTIONS_REGEX
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
from markdown_novel_tools.outline import beats_helper, get_beats
from markdown_novel_tools.repo import commits_today, replace
from markdown_novel_tools.shunn import shunn_docx, shunn_md
from markdown_novel_tools.utils import find_markdown_files, write_to_file


def novel_beats(args):
    """Print an outline's beats in the desired form."""
    path = Path(args.path or config["outline"]["single"]["primary_outline_file"])

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

    stdout, stderr = beats_helper(
        args.path,
        column=args.column,
        filter_=args.filter,
        file_headers=args.file_headers,
        multi_table_output=args.multi_table_output,
        order=args.order,
        split_columns=args.split_column,
        also_split_by_slash=args.also_split_by_slash,
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


def novel_links(args):
    """Get the obsidian links for the manuscript"""
    files = find_markdown_files(args.path)
    links = set()
    errors = ""
    exit_code = 0
    for path in files:
        markdown_file = get_markdown_file(path)
        for link in re.findall(LINKS_REGEX, markdown_file.body):
            links.add(link)
    for link in sorted(links, key=str.lower):
        print(link)


def novel_new(args):
    """Create a new file from template."""

    path = Path(args.path)
    template = Path(args.config["markdown_template_dir"]) / f"{args.template}.md"
    if args.create_missing_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy(template, path)


def novel_outline_convert(args):
    """Convert the outline to something shareable."""
    path = Path(config["outline"]["single"]["primary_outline_file"])
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
    contents, stats = beats_helper(
        path,
        column="Arc",
        multi_table_output=True,
        split_columns=["Arc", "Beat"],
        stats=True,
        format_="html",
        beats_type="arcs",
    )
    write_to_file(parent / f"{output_basestr}-arcs.html", contents)

    # Scene
    contents, stats = beats_helper(
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


def arc_grep(beats_contents, regex):
    """Grep through the contents of the arc"""
    parsed_contents = ""
    in_table = False
    table_contents = ""
    for line in beats_contents.splitlines():
        if line.startswith("|"):
            if not in_table:
                in_table = True
            elif not line.startswith("|-") and not re.search(
                regex,
                line,
            ):
                continue
            table_contents = f"{table_contents}{line}\n"
        else:
            if in_table:
                if table_contents.count("\n") > 2:
                    parsed_contents = f"{parsed_contents}{table_contents}"
                parsed_contents = f"{parsed_contents}\n"
                in_table = False
                table_contents = ""
            else:
                parsed_contents = f"{parsed_contents}{line}\n"
    if table_contents.count("\n") > 2:
        parsed_contents = f"{parsed_contents}{table_contents}"
    return parsed_contents


def create_single_sync_set(paths, parent, primary_outline_type, output_name):
    """Create the different output_paths outlines, using `paths` as the source, for a single book or series."""
    output_paths = {
        "full": parent / output_name.format(outline_type="full"),
        "scenes": parent / output_name.format(outline_type="scenes"),
        "povs": parent / output_name.format(outline_type="povs"),
        "arcs": parent / output_name.format(outline_type="arcs"),
        "questions": parent / output_name.format(outline_type="questions"),
        "beats": parent / output_name.format(outline_type="beats"),
    }

    parent.mkdir(parents=True, exist_ok=True)

    match primary_outline_type:
        case "scenes":
            contents, stats = beats_helper(paths, column="Scene", file_headers=True, stats=True)
        case "povs":
            contents, stats = beats_helper(paths, column="POV", file_headers=True, stats=True)
        case "full":
            contents, stats = beats_helper(paths, file_headers=True, stats=True)
        case _:
            raise KeyError(f"Invalid primary_outline_type {primary_outline_type}!")

    write_to_file(output_paths["full"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # POVS
    contents, stats = beats_helper(
        output_paths["full"],
        column="POV",
        file_headers=True,
        multi_table_output=True,
        stats=True,
        beats_type="povs",
    )
    write_to_file(output_paths["povs"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Arc
    contents, stats = beats_helper(
        output_paths["full"],
        column="Arc",
        file_headers=True,
        multi_table_output=True,
        split_columns=["Arc", "Beat"],
        stats=True,
        beats_type="arcs",
    )
    write_to_file(output_paths["arcs"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Scene
    contents, stats = beats_helper(
        output_paths["full"],
        column="Scene",
        file_headers=True,
        multi_table_output=True,
        stats=True,
        beats_type="scenes",
    )
    write_to_file(output_paths["scenes"], contents)
    print(f"{stats}\n", file=sys.stderr)

    # Questions - regex is hacky but I don't have a way to split and filter by different columns
    arc_contents, stats = beats_helper(
        output_paths["full"],
        column="Arc",
        file_headers=True,
        multi_table_output=True,
        split_columns=["Arc", "Beat"],
        also_split_by_slash=True,
        stats=True,
        beats_type="questions",
    )
    parsed_contents = arc_grep(arc_contents, QUESTIONS_REGEX)
    write_to_file(output_paths["questions"], parsed_contents)
    print(f"{stats}\n", file=sys.stderr)

    # Beats - regex is hacky but I don't have a way to split and filter by different columns
    arc_contents, stats = beats_helper(
        output_paths["full"],
        column="Arc",
        file_headers=True,
        multi_table_output=True,
        split_columns=["Arc", "Beat"],
        also_split_by_slash=True,
        stats=True,
        beats_type="beats",
    )
    parsed_contents = arc_grep(arc_contents, BEATS_REGEX)
    write_to_file(output_paths["beats"], parsed_contents)
    print(f"{stats}\n", file=sys.stderr)


def run_single_sync(config, book_num=None, path=None, artifact_dir=None, primary_outline_type=None):
    """Sync the outline files for a single book, or combine the existing book outlines into a single series.

    Note, if we're running run_single_sync for a series, we will not pick up new outline changes in each book,
    unless they're synced to each book's primary outline files. If we want to sync those first, use the
    `--all` option to call `sync_each_book_in_a_series` first.
    """
    if book_num:
        config_key = "single"
        print(f"Syncing book {book_num}...")
    else:
        config_key = "series"
        print(f"Syncing the series...")

    if path:
        paths = [Path(path)]
    elif book_num:
        paths = [Path(config["outline"]["single"]["primary_outline_file"])]
    else:
        paths = [Path(p) for p in glob(config["outline"]["series"]["source_outline_glob"])]

    if artifact_dir:
        parent = Path(artifact_dir)
    else:
        parent = Path(config["outline"][config_key]["output_dir"])

    primary_outline_type = (
        primary_outline_type or config["outline"][config_key]["primary_outline_type"]
    )
    output_name = config["outline"][config_key]["output_name"]

    create_single_sync_set(paths, parent, primary_outline_type, output_name)


def sync_each_book_in_a_series(config, **kwargs):
    """Sync the outline of each book in a series. This allows us to sync the latest changes into the series outline."""
    path_names = glob(config["outline"]["series"]["source_outline_glob"])
    for path_name in path_names:
        single_kwargs = deepcopy(kwargs)
        single_config = deepcopy(config)
        m = re.search(config["outline"]["series"]["source_outline_regex"], path_name)
        if m:
            single_kwargs["book_num"] = m["book_num"]
            repl_dict = {"book_num": m["book_num"], "outline_type": "{outline_type}"}
            single_config = get_new_config_val(single_config, {}, repl_dict=repl_dict)
            run_single_sync(single_config, **single_kwargs)


def novel_sync(args):
    """Sync the various outline files in a given book."""

    kwargs = {
        "book_num": args.config["book_num"],
        "path": args.path,
        "artifact_dir": args.artifact_dir,
        "primary_outline_type": args.primary_outline_type,
    }

    if args.all:
        if args.config["book_num"]:
            print(f"book_num is {book_num}; --all doesn't work for a single book!")
            raise SystemExit(1)
        else:
            sync_each_book_in_a_series(args.config, **kwargs)

    print("Finished sync_each_book_in_a_series")

    run_single_sync(args.config, **kwargs)


def novel_today(args):
    """Get daily stats."""
    # pylint: disable=unused-argument
    commits = commits_today(args.config)

    commit_string = "\n".join(commits[::-1])
    print(f"""{commit_string}""")
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
    beats_parser = subparsers.add_parser("beats", help="Show the outline beats")
    beats_parser.set_defaults(require_book_num=False)
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
    beats_parser.add_argument("--also-split-by-slash", help="Split column by slash.", default=False)
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
    sync_parser.set_defaults(require_book_num=False)
    sync_parser.add_argument("--artifact-dir", help="Defaults to the parent of PATH")
    sync_parser.add_argument(
        "--all", "-a", action="store_true", help="Sync all the outlines of a series."
    )
    sync_parser.add_argument(
        "--primary-outline-type",
        choices=("scenes", "povs", "full"),
        help="The type of outline we're reading from.",
    )
    sync_parser.add_argument(
        "path", nargs="?", help="Defaults to the config or default primary outline path."
    )
    sync_parser.set_defaults(func=novel_sync)

    # novel convert
    convert_parser = subparsers.add_parser(
        "convert", help="Convert manuscript markdown into various other formats."
    )
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
    lint_parser = subparsers.add_parser(
        "lint", help="Check the manuscript files for syntax correctness."
    )
    lint_parser.add_argument("-f", "--fix", action="store_true")
    lint_parser.add_argument("path")
    lint_parser.set_defaults(func=novel_lint)

    # novel links
    links_parser = subparsers.add_parser("links", help="Show the wiki pages linked from the path.")
    links_parser.add_argument("path")
    links_parser.set_defaults(func=novel_links)

    # novel new
    new_parser = subparsers.add_parser("new", help="Create a file from the appropriate template.")
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
    outline_convert_parser = subparsers.add_parser(
        "outline_convert", help="Convert outline markdown into various other formats."
    )
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
    replace_parser = subparsers.add_parser(
        "replace", help="Globally replace words or phrases in the path."
    )
    replace_parser.add_argument(
        "-l",
        "--list",
        action=argparse.BooleanOptionalAction,
        help="Only show what would be replaced, without making the changes.",
    )
    replace_parser.add_argument("from_")
    replace_parser.add_argument("to")
    replace_parser.set_defaults(func=replace)

    # novel stats
    stats_parser = subparsers.add_parser("stats", help="Show the novel stats.")
    stats_parser.set_defaults(require_book_num=True)
    stats_parser.set_defaults(func=novel_stats)

    # novel today
    today_parser = subparsers.add_parser(
        "today", help="Show the commits made in the repository today."
    )
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
