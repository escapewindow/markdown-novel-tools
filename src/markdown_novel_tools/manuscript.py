#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

import glob
from pathlib import Path
import sys

import yaml


from markdown_novel_tools.constants import OUTLINE_SCENE_RE
from markdown_novel_tools.outline import do_parse_file, get_beats, parse_beats_args
from markdown_novel_tools.scene import MarkdownFile


def summary_tool():
    """Work on summaries in both the outline and scene(s)."""
    outline_argv = ["-c", "2", "-f", "01.01", "-y", "outline/Book 1 outline/scenes.md"]
    args = parse_beats_args(outline_argv)
    with open(args.path, encoding="utf-8") as fh:
        table = do_parse_file(fh, args)
    if table:
        stdout, stderr = get_beats(table, args)
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
