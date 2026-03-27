"""Test outline."""

import pytest

import markdown_novel_tools.outline as outline


def test_table():
    pass


def test_outline_to_yaml():
    pass


@pytest.mark.parametrize(
    "line, split_column, expected",
    (
        ("| One | Two | Three | Four |", [], ["One", "Two", "Three", "Four"]),
        ("| One | Two,Three | Four | Five |", [1], ["One", ["Two", "Three"], "Four", "Five"]),
        ("| One | Two,Three | Four | Five |", [], ["One", "Two,Three", "Four", "Five"]),
    ),
)
def test_get_line_parts(line, split_column, expected):
    assert outline.get_line_parts(line, split_column=split_column) == expected


def test_get_outline_file_header():
    assert outline.get_outline_file_header("arcs") == """---
tags: ['arcs', 'outline']
aliases: []
---

# Arcs

"""


def test_beats():
    pass


def test_build_table_from_file():
    pass


def test_get_markdown_table_header():
    header = "| foo | bar | baz | longer bit |"
    line = "|-----|-----|-----|------------|"
    assert outline.get_markdown_table_header(header) == f"{header}\n{line}"


@pytest.mark.parametrize(
    "header_text, expected",
    (
        ("Test", "test"),
        ("Test___", "test"),
        ("Can't stop", "cant-stop"),
        ("Won't ???Stop", "wont-stop"),
    ),
)
def test_header_text_to_header_anchor(header_text, expected):
    assert outline.header_text_to_header_anchor(header_text) == expected


def test_get_markdown_from_table():
    pass


def test_get_yaml_from_table():
    pass


def test_get_html_from_table():
    pass
