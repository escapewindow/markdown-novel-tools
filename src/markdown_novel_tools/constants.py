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

# Config {{{1

DEFAULT_CONFIG = {
    "timezone": "US/Mountain",
    "outline": {
        "outline_dir": "outline/Book {book_num} outline/",
        "primary_outline_file": "scenes.md",
    },
    "convert": {
        "metadata_path": "skeleton/Book {book_num} Metadata.txt",
        "frontmatter_files": [
            "skeleton/Book {book_num} Copyright.md",
            "skeleton/Book {book_num} Dedication.md",
            "skeleton/Book {book_num} Author's Note.md",
            "skeleton/Book {book_num} Pronunciation Guide.md",
        ],
    },
    "find_files_by_name_cmd": ["fd", "-s", "-F", "-E", "snippets"],
    "find_files_by_content_cmd": ["rg", "-F", "-l"],
}

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
