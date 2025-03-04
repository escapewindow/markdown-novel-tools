#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

import glob
from pathlib import Path

import yaml

from markdown_novel_tools.constants import OUTLINE_SCENE_RE
from markdown_novel_tools.outline import do_parse_file, parse_beats_args
from markdown_novel_tools.scene import MarkdownFile

