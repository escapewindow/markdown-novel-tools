#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""
# TODO frontmatter schema

import os
import subprocess
import sys
import time
from copy import deepcopy
from difflib import unified_diff
from glob import glob
from io import StringIO
from pathlib import Path
from pprint import pprint

import yaml
from git import Repo

from markdown_novel_tools.constants import MANUSCRIPT_RE, OUTLINE_SCENE_RE
from markdown_novel_tools.outline import do_parse_file, get_beats, parse_beats_args
from markdown_novel_tools.scene import get_markdown_file
from markdown_novel_tools.utils import local_time, yaml_string


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

    if diff:
        print(diff)


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
            previous_commit = rev
            break
        count += 1

    print(f"{count} commits today.")


def diff_frontmatter():
    """Diff frontmatter.

    TODO parse args, stop hardcoding
    """

    files = sorted(glob("manuscript/Book 1/*"))
    table = None

    # Diff summaries
    for _path in files:
        m = MANUSCRIPT_RE.match(os.path.basename(_path))
        if not m:
            continue

        outline_argv = [
            "-c",
            "2",
            "-f",
            f"{m['chapter_num']}.{m['scene_num']}",
            "-y",
            "outline/Book 1 outline/scenes.md",
        ]
        args = parse_beats_args(outline_argv)
        if not table:
            with open(args.path, encoding="utf-8") as fh:
                table = do_parse_file(fh, args)

        outline_summary, _ = get_beats(table, args)

        markdown_file = get_markdown_file(_path)
        scene_summary = yaml_string(markdown_file.parsed_yaml["Summary"])

        base_filename = os.path.basename(_path).strip(".md")
        diff_yaml(
            scene_summary,
            outline_summary,
            from_name=f"{base_filename} scene",
            to_name=f"{base_filename} outline",
            verbose=False,
        )


def query_frontmatter():
    """Query frontmatter.

    TODO parse args, stop hardcoding
    """
    files = sorted(glob("manuscript/Book 1/1_01_01*"))
    if len(files) < 1:
        raise OSError("Unable to find a matching scene!")
    if len(files) > 1:
        raise OSError(f"Found too many matching scenes: {files}!")
    query_field = "Summary"

    # Diff summaries
    markdown_file = get_markdown_file(files[0])
    print(yaml_string(markdown_file.parsed_yaml[query_field]), end="")


def frontmatter_tool():
    """Work on summaries in both the outline and scene(s)."""

    # TODO proper argparse
    #  - create base parser
    #    - base parser_check
    #  - add summary args
    #    - summary parser_check

    if len(sys.argv) < 1 or sys.argv[1] == "diff":
        return diff_frontmatter()
    elif sys.argv[1] == "query":
        return query_frontmatter()

    # TODO replace summary; diff scene
    # TODO overwrite scene
