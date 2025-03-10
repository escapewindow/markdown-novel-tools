#!/usr/bin/env python3
"""markdown-novel-tools constants."""

import re

from schema import And, Or, Schema, Use

# TODO unhardcode
TIMEZONE = "US/Mountain"
DEBUG = 0

ALPHANUM_RE = re.compile(r"""\w""")
DIVIDER_REGEX = re.compile(r"""^[|\-\s]*$""")

FILE_HEADER = """---
cssClass: "wide-table"
---

# Outline
"""

# Regex {{{1
OUTLINE_SCENE_RE = re.compile(
    r"""^((?P<book_num>\d*)\.)?(?P<chapter_num>\d+)\.(?P<scene_num>\d+)$"""
)
MANUSCRIPT_RE = re.compile(
    r"""^(?P<book_num>\d+)[-_](?P<chapter_num>\d+)[-_](?P<scene_num>\d+) - (?P<POV>\S+)"""
)
SPECIAL_CHAR_REGEX = re.compile(r"""[^A-Za-z0-9 ]""")

# Schema {{{1
FRONTMATTER_SCHEMA = Schema(
    {
        "Title": And(str, len),
        "tags": list,
        "aliases": list,
        "Locations": And(list, len),
        "Characters": And(list, len),
        "POV": And(str, len),
        "Hook": And(str, len),
        "Scene": And(dict, lambda n: n.keys() == ["Goal", "Conflict", "Setback"]),
        "Sequel": And(dict, lambda n: n.keys() == ["Reaction", "Dilemma", "Decision"]),
        "Cliffhanger": And(str, len),
        "Summary": (list, len),
    }
)
