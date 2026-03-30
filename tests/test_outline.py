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
    "line, split_columns, expected",
    (
        ("| One | Two | Three | Four |", [], ["One", "Two", "Three", "Four"]),
        ("| One | Two,Three | Four | Five |", [1], ["One", ["Two", "Three"], "Four", "Five"]),
        ("| One | Two,Three | Four | Five |", [], ["One", "Two,Three", "Four", "Five"]),
    ),
)
def test_get_line_parts(line, split_columns, expected):
    assert outline.get_line_parts(line, split_columns=split_columns) == expected


def test_get_outline_file_header():
    assert outline.get_outline_file_header("arcs") == """---
tags: ['arcs', 'outline']
aliases: []
---

# Arcs

"""


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


def test_table_markdown_simple():
    """Build a table; get_markdown_from_table should result in the same file."""
    path = TEST_DATA_DIR / "matrix-full.md"
    with open(path) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(path)
    mdoutput = outline.get_markdown_from_table(table)
    header = outline.get_outline_file_header("outline")
    assert f"{header}{mdoutput}" == contents
    beats_stdout, beats_stderr = outline.get_beats(table, file_headers=header, stats=True)
    assert beats_stdout == contents
    assert beats_stderr == """Num beats: 49"""


def test_table_yaml_simple():
    path = TEST_DATA_DIR / "test-simple.md"
    table = outline.build_table_from_file(path)
    yamloutput = outline.get_yaml_from_table(table)
    beats_stdout, _ = outline.get_beats(table, format_="yaml")
    with open(TEST_DATA_DIR / "test-simple.yaml") as fh:
        expected = fh.read()
    assert yamloutput == expected
    assert yamloutput == beats_stdout


def test_table_html_simple():
    path = TEST_DATA_DIR / "test-simple.md"
    table = outline.build_table_from_file(path)
    htmloutput = outline.get_html_from_table(table)
    with open(TEST_DATA_DIR / "test-simple.html") as fh:
        expected = fh.read()
    assert htmloutput == expected
    beats_stdout, _ = outline.get_beats(table, format_="html")
    assert beats_stdout == expected


def test_beats_bad_format():
    path = TEST_DATA_DIR / "test-simple.md"
    table = outline.build_table_from_file(path)
    with pytest.raises(Exception):
        outline.get_beats(table, format_="invalid format")


def test_table_from_multi():
    """Parse scenes, which is multi-table, and compare against full outline"""
    scenes_path = TEST_DATA_DIR / "matrix-scenes.md"
    full_path = TEST_DATA_DIR / "matrix-full.md"
    table = outline.build_table_from_file(scenes_path)
    with open(full_path) as fh:
        full_contents = fh.read()
    header = outline.get_outline_file_header("outline")
    mdoutput = outline.get_markdown_from_table(table)
    assert f"{header}{mdoutput}" == full_contents
    beats_stdout, beats_stderr = outline.get_beats(table, file_headers=True, stats=True)
    assert beats_stdout == full_contents
    assert beats_stderr == """Num beats: 49"""


def test_full_table_to_scenes():
    """Parse full, and compare against scenes, which is multi-table"""
    full_path = TEST_DATA_DIR / "matrix-full.md"
    scenes_path = TEST_DATA_DIR / "matrix-scenes.md"
    table = outline.build_table_from_file(full_path, column="Scene")
    with open(scenes_path) as fh:
        scenes_contents = fh.read()
    header = outline.get_outline_file_header("scenes")
    mdoutput = outline.get_markdown_from_table(
        table,
        multi_table=True,
    )
    assert f"{header}{mdoutput}" == scenes_contents
    beats_stdout, beats_stderr = outline.get_beats(
        table,
        file_headers=True,
        stats=True,
        beats_type="scenes",
        multi_table_output=True,
    )
    assert beats_stdout == scenes_contents
    assert (
        beats_stderr
        == """Num values: 22 ['01.01', '01.02', '02.01', '02.02', '02.03', '03.01', '04.01', '05.02', '05.03', '06.01', '06.02', '07.01', '07.02', '08.01', '09.01', '10.01', '11.01', '12.01', '12.02', '13.01', '13.02', '14.01']
Num beats: 49"""
    )


def test_table_order_invalid():
    path = TEST_DATA_DIR / "test-simple.md"
    with pytest.raises(SystemExit):
        outline.build_table_from_file(path, order=["invalid", "column", "names"])


@pytest.mark.parametrize(
    "path",
    (
        TEST_DATA_DIR / "test-multi-extra-header.md",
        TEST_DATA_DIR / "test-multi-missing-header.md",
    ),
)
def test_table_from_multi_invalid_headers(path):
    with pytest.raises(SystemExit):
        outline.build_table_from_file(path)


def test_filter_order():
    """Build a table; change the column order and filter by scene."""
    full_path = TEST_DATA_DIR / "test-simple.md"
    second_scene_path = TEST_DATA_DIR / "test-simple-second-scene.md"
    with open(second_scene_path) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(
        full_path,
        order=["Description", "POV", "Beat", "Scene", "Arc"],
        column="Scene",
    )
    mdoutput = outline.get_markdown_from_table(table, filter_=["02.01"], multi_table=True)
    header = outline.get_outline_file_header("scenes")
    assert f"{header}{mdoutput}" == contents
    beats_stdout, beats_stderr = outline.get_beats(
        table,
        file_headers=True,
        stats=True,
        beats_type="scenes",
        multi_table_output=True,
        filter_=["02.01"],
    )
    assert beats_stdout == contents
    assert beats_stderr == """Num values: 1 ['02.01']
Num beats: 1"""


@pytest.mark.parametrize(
    "expected_file, also_split_by_slash, filter_",
    (
        (TEST_DATA_DIR / "test-simple-split_columns.md", True, ["Hook"]),
        (TEST_DATA_DIR / "test-simple-split_columns-noslash.md", False, []),
        (TEST_DATA_DIR / "test-simple-filter.md", False, ["Hook/Question"]),
        (TEST_DATA_DIR / "test-simple-filter.md", False, ["Question"]),
    ),
)
def test_filter_split_columns(expected_file, also_split_by_slash, filter_):
    """Build a table; get_markdown_from_table should result in the same file."""
    full_path = TEST_DATA_DIR / "test-simple.md"
    with open(expected_file) as fh:
        contents = fh.read()
    table = outline.build_table_from_file(
        full_path,
        column="Beat",
        split_columns=["Beat", "Arc"],
        also_split_by_slash=also_split_by_slash,
    )
    mdoutput = outline.get_markdown_from_table(table, filter_=filter_, multi_table=True)
    header = outline.get_outline_file_header("beats")
    assert f"{header}{mdoutput}" == contents
