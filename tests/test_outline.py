"""Test outline."""

import markdown_novel_tools.outline as outline


def test_table():
    pass


def test_outline_to_yaml():
    pass


def test_get_line_parts():
    pass


def test_get_outline_file_header():
    assert outline.get_outline_file_header("arcs") == """---
tags: ['arcs', 'outline']
aliases: []
---

# Arcs

"""
