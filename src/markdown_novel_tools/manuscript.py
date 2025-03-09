#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

import argparse
import os
import re
import time
from difflib import unified_diff
from glob import glob
from pathlib import Path

from git import Repo

from markdown_novel_tools.constants import MANUSCRIPT_RE
from markdown_novel_tools.outline import do_parse_file
from markdown_novel_tools.scene import get_markdown_file
from markdown_novel_tools.utils import find_markdown_files, local_time, yaml_string


def diff_yaml(from_yaml, to_yaml, from_name="from", to_name="to", verbose=False):
    """Diff outline and scene yaml strings."""
    if verbose:
        print(from_yaml, end="")
        print(to_yaml, end="")

    diff = ""
    for line in unified_diff(
        from_yaml.splitlines(), to_yaml.splitlines(), fromfile=from_name, tofile=to_name
    ):
        diff = f"{diff}{line.rstrip()}\n"

    return diff


def today():
    """Print the number of git commits in cwd today."""
    path = Path(os.getcwd())
    repo = Repo(path)
    time_fmt = "%Y%m%d"
    today = local_time(time.time()).strftime(time_fmt)
    current_commit = repo.head.commit
    current_commit_date = local_time(current_commit.committed_date).strftime(time_fmt)
    count = 0
    for rev in repo.iter_commits(repo.head.ref):
        if local_time(rev.committed_date).strftime(time_fmt) != today:
            break
        count += 1

    print(f"{count} commits today.")


# Frontmatter {{{1
def diff_frontmatter(args):
    """Diff frontmatter."""

    files = find_markdown_files(args.path)
    table = None

    # Diff summaries
    for _path in files:
        m = MANUSCRIPT_RE.match(os.path.basename(_path))
        if not m:
            continue

        if not table:
            with open(args.outline, encoding="utf-8") as fh:
                table = do_parse_file(fh, column="Scene")

        outline_summary = table.get_yaml(_filter=[f"{m['chapter_num']}.{m['scene_num']}"])

        markdown_file = get_markdown_file(_path)
        scene_summary = yaml_string(markdown_file.parsed_yaml["Summary"])

        base_filename = re.sub("\.md$", "", os.path.basename(_path))
        diff = diff_yaml(
            scene_summary,
            outline_summary,
            from_name=f"{base_filename} scene",
            to_name=f"{base_filename} outline",
            verbose=False,
        )
        if diff:
            print(diff, end="")


def query_frontmatter(args):
    """Query frontmatter."""
    files = find_markdown_files(args.path)

    # Diff summaries
    for path in files:
        markdown_file = get_markdown_file(path)
        if args.field:
            print(yaml_string(markdown_file.parsed_yaml[args.field]), end="")
        else:
            print(yaml_string(markdown_file.parsed_yaml), end="")


def frontmatter_parser():
    """Return a parser for the frontmatter tool."""
    parser = argparse.ArgumentParser(prog="frontmatter")
    parser.add_argument("-v", "--verbose", help="Verbose logging.")
    subparsers = parser.add_subparsers()

    # frontmatter query
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("-f", "--field")
    query_parser.add_argument("path", nargs="+")
    query_parser.set_defaults(func=query_frontmatter)

    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument(
        "-o", "--outline", default="outline/Book 1 outline/scenes.md"
    )  # TODO unhardcode
    diff_parser.add_argument("path", nargs="+")
    diff_parser.set_defaults(func=diff_frontmatter)

    # TODO frontmatter schema. `frontmatter check`?
    # TODO replace summary. `frontmatter update`?
    # TODO overwrite scene.

    return parser


def frontmatter_tool():
    """Work on summaries in both the outline and scene(s)."""

    parser = frontmatter_parser()
    args = parser.parse_args()
    args.func(args)
