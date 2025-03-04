#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""
# TODO frontmatter schema

import os
import sys
from copy import deepcopy
from difflib import unified_diff
from glob import glob
from io import StringIO
from pathlib import Path

import yaml

from markdown_novel_tools.constants import OUTLINE_SCENE_RE
from markdown_novel_tools.outline import do_parse_file, get_beats, parse_beats_args
from markdown_novel_tools.scene import get_markdown_file
from markdown_novel_tools.utils import yaml_string


def diff_yaml(outline_yaml, scene_yaml, verbose=False):
    """Diff outline and scene yaml strings."""
    if verbose:
        print(outline_yaml, end="")

    d = "\n".join(
        unified_diff(
            outline_yaml.splitlines(),
            scene_yaml.splitlines(),
            "Outline",
            "Scene",
        )
    )
    if d:
        print(f"Diff!\n{d}")
    else:
        print("Matches.")


def frontmatter_tool():
    """Work on summaries in both the outline and scene(s)."""

    # TODO proper argparse
    #  - create base parser
    #    - base parser_check
    #  - add summary args
    #    - summary parser_check
    outline_argv = ["-c", "2", "-f", "01.01", "-y", "outline/Book 1 outline/scenes.md"]
    args = parse_beats_args(outline_argv)
    with open(args.path, encoding="utf-8") as fh:
        table = do_parse_file(fh, args)
    if table:
        outline_summary, _ = get_beats(table, args)

    files = glob("manuscript/Book 1/1_01_01*")
    if len(files) < 1:
        raise OSError("Unable to find a matching scene!")
    if len(files) > 1:
        raise OSError(f"Found too many matching scenes: {files}!")

    # Diff summaries
    markdown_file = get_markdown_file(files[0])
    scene_summary = yaml_string(markdown_file.parsed_yaml["Summary"])
    diff_yaml(outline_summary, scene_summary)

    outline_yaml = deepcopy(markdown_file.parsed_yaml)
    outline_yaml["Summary"] = yaml.safe_load(StringIO(outline_summary))
    outline_frontmatter = yaml_string(outline_yaml)
    print(f"---\n{outline_frontmatter}\n---\n{markdown_file.yaml}")
    diff_yaml(outline_frontmatter, markdown_file.yaml)

    # TODO replace summary; diff scene
    # TODO overwrite scene
