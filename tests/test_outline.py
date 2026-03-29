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
    """Build a table; get_markdown_from_table should result in the same file."""
    path = TEST_DATA_DIR / "matrix-full.md"
    with open(path) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(path)
    mdoutput = outline.get_markdown_from_table(table)
    header = outline.get_outline_file_header("outline")
    assert f"{header}{mdoutput}" == contents


def test_get_yaml_from_table():
    path = TEST_DATA_DIR / "matrix-simple.md"
    table = outline.build_table_from_file(path)
    yamloutput = outline.get_yaml_from_table(table)
    assert yamloutput == """- Trinity took an extra shift to watch Neo. (The One Hook, Trinity Hook)
- Neo - Whoa. (Spoon)
- Neo - surprised - tests the mdash. (Mdash)
"""


def test_get_html_from_table():
    path = TEST_DATA_DIR / "matrix-simple.md"
    table = outline.build_table_from_file(path)
    htmloutput = outline.get_html_from_table(table)
    table_header = """<table><tr>
  <th>Description</th>
  <th>POV</th>
  <th>Scene</th>
  <th>Arc</th>
  <th>Beat</th>
</tr>"""
    expected = f"""{outline.OUTLINE_HTML_HEADER}{table_header}
<tr>
  <td>Trinity took an extra shift to watch Neo.</td>
  <td>Trinity</td>
  <td>01.01</td>
  <td>The One,Trinity</td>
  <td>Hook,Hook</td>
</tr>
<tr>
  <td>Neo: Whoa.</td>
  <td>Neo</td>
  <td>02.01</td>
  <td>Spoon</td>
  <td></td>
</tr>
<tr>
  <td>Neo&mdash;surprised&mdash;tests the mdash.</td>
  <td>Neo</td>
  <td>13.02</td>
  <td>Mdash</td>
  <td></td>
</tr>
</table>
</body></html>
"""
    assert htmloutput == expected
