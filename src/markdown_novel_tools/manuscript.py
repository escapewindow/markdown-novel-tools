#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

from difflib import unified_diff
from glob import glob
import os
from pathlib import Path
import sys

import yaml


from markdown_novel_tools.constants import OUTLINE_SCENE_RE
from markdown_novel_tools.outline import do_parse_file, get_beats, parse_beats_args
from markdown_novel_tools.scene import get_markdown_file, get_summary


def summary_tool():
    """Work on summaries in both the outline and scene(s)."""
    outline_argv = ["-c", "2", "-f", "01.01", "-y", "outline/Book 1 outline/scenes.md"]
    args = parse_beats_args(outline_argv)
    with open(args.path, encoding="utf-8") as fh:
        table = do_parse_file(fh, args)
    if table:
        stdout, stderr = get_beats(table, args)

    files = glob("manuscript/Book 1/1_01_01*")
    if len(files) < 1:
        raise OSError("Unable to find a matching scene!")
    if len(files) > 1:
        raise OSError(f"Found too many matching scenes: {files}!")
    markdown_file = get_markdown_file(files[0])
    scene_summary = get_summary(markdown_file)

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr)
    d = "\n".join(
        unified_diff(
            stdout.splitlines(),
            scene_summary.splitlines(),
            "Outline",
            "Scene",
        )
    )
    if d:
        print(f"Diff!\n{d}")
    else:
        print("Matches.")
