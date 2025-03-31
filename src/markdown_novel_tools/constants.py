#!/usr/bin/env python3
"""markdown-novel-tools constants."""

import os
import re

DEBUG = 0

OUTLINE_FILE_HEADER = """---
cssClass: "wide-table"
---

# Outline
"""

# Regex {{{1
ALPHANUM_REGEX = re.compile(r"""\w""")
SPECIAL_CHAR_REGEX = re.compile(r"""[^A-Za-z0-9 ]""")

MANUSCRIPT_REGEX = re.compile(
    r"""^(?P<book_num>\d+)[-_](?P<chapter_num>\d+)[-_](?P<scene_num>\d+) - (?P<POV>\S+)"""
)

OUTLINE_SCENE_REGEX = re.compile(
    r"""^((?P<book_num>\d*)\.)?(?P<chapter_num>\d+)\.(?P<scene_num>\d+)$"""
)

TABLE_DIVIDER_REGEX = re.compile(r"""^[|\-\s]*$""")
