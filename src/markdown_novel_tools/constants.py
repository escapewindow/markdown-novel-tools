#!/usr/bin/env python3
"""markdown-novel-tools constants."""

import re

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
OUTLINE_SCENE_RE = re.compile(r"""^((?P<book_num>\d*)\.)?(?P<chapter_num>\d+)\.(?P<scene_num>\d+)$""")
MANUSCRIPT_FILENAME_RE = re.compile(r"""^(?P<book_num>\d+)_(?P<chapter_num>\d+)_(?P<scene_num>\d+) - """)
SPECIAL_CHAR_REGEX = re.compile(r"""[^A-Za-z0-9 ]""")
