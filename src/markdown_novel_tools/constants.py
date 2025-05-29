#!/usr/bin/env python3
"""markdown-novel-tools constants."""

import os
import re
from pathlib import Path

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
        "outline_dir": "outline/Book {book_num}/",
        "primary_outline_file": "book{book_num}-scenes.md",
    },
    "convert": {
        "metadata_path": {
            "default": "skeleton/Book {book_num} Metadata.txt",
        },
        "frontmatter_files": [
            "skeleton/Book {book_num} Copyright.md",
            "skeleton/Book {book_num} Dedication.md",
        ],
        "css": {
            # TODO works in develop env, need an install fix
            "css_dir": str(Path(__file__).parent.parent.parent / "data" / "css"),
            "manuscript_pdf_css_path": "pdf-light.css",
            "misc_pdf_css_path": "pdf-misc.css",
            "epub_css_path": "epub.css",
        },
        "shunn_repo_url": "https://github.com/escapewindow/pandoc-templates",
        "shunn_repo_path": None,
    },
    # TODO works in develop env, need an install fix
    "markdown_template_dir": str(
        Path(__file__).parent.parent.parent / "data" / "markdown-templates"
    ),
    "find_files_by_name_cmd": ["fd", "-s", "-F", "-E", "snippets"],
    "find_files_by_content_cmd": ["rg", "-F", "-l"],
}


# Outline {{{1
VALID_PRIMARY_OUTLINE_FILENAMES = ("book{book_num}-scenes.md", "book{book_num}-full.md")

OUTLINE_HTML_HEADER = """<html><head><style>
    table, th, td {
      border: 1px solid black;
      border-collapse: collapse;
      padding: 10px;
    }
</style></head><body>
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
