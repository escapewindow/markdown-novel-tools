"""Test outline."""

import pytest

import markdown_novel_tools.outline as outline

from . import TEST_DATA_DIR


@pytest.mark.parametrize(
    "column, expected, throws",
    (
        (2, 2, False),
        ("POV", 1, False),
        (20, None, IndexError),
        ("Fake column name", None, ValueError),
    ),
)
def test_table_get_column(column, expected, throws):
    path = TEST_DATA_DIR / "matrix-full.md"
    with open(path) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(path)
    if throws:
        with pytest.raises(throws):
            table.get_column(column)
    else:
        assert table.get_column(column) == expected


def test_outline_to_yaml():
    from_ = r'"[[foo]] "bar": blah de blah"'
    to = "foo bar - blah de blah"
    assert outline._outline_to_yaml(from_) == to


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


def test_get_beats():
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
    path = TEST_DATA_DIR / "matrix-full.md"
    with open(path) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(path)
    mdoutput = outline.get_markdown_from_table(table)
    with open(TEST_DATA_DIR / "test_output.md", "w") as fh:
        fh.write(mdoutput)
    header = outline.get_outline_file_header("outline")
    assert f"{header}{outline.get_markdown_from_table(table)}" == contents


def test_get_yaml_from_table():
    pass


def test_get_html_from_table():
    pass
