#!/usr/bin/env python3
"""Parse a markdown outline.

Allows for filtering by and reordering of columns.
Currently assumes that all tables in a file are formatted the same.
"""

import re
import sys
from collections import namedtuple
from itertools import zip_longest
from urllib.parse import quote

from markdown_novel_tools.constants import (
    OUTLINE_HTML_HEADER,
    SPECIAL_CHAR_REGEX,
    TABLE_DIVIDER_REGEX,
)
from markdown_novel_tools.utils import split_by_char


class Table:
    """Table object."""

    def __init__(self, line, column=None, order=None, split_column=None):
        """Init Table object."""
        parts = get_line_parts(line)
        self.line_obj = namedtuple("Line", parts)
        self.max_width = [len(x) for x in parts]
        self.split_column = split_column
        self.order = self.line_obj._fields
        if order is not None:
            self.verify_field_names(order, "order")
            self.order = tuple(order)
        if split_column is not None:
            for i, val in enumerate(split_column):
                split_column[i] = self.get_column(val)
            self.split_column = tuple(split_column)
        self.column = self.get_column(column)
        self.parsed_lines = {}
        self.line_count = 0
        self.column_values = set()

    def get_column(self, column):
        """Get the column name, given either an int or a column name"""
        if column is None:
            return column
        try:
            column = int(column)
            if column < len(self.order):
                return column
            raise IndexError(f"{column} is out of range in {self.order}")
        except ValueError:
            if column in self.order:
                return self.order.index(column)
            print(f"{column} is not a column name or index: {self.order}")
            raise

    def verify_field_names(self, fields, column_name):
        """Verify the fields in `order` are valid column names."""
        error_msg = ""
        for field in fields:
            if field not in self.line_obj._fields:
                error_msg += f"{column_name}: {field} is not a valid field!\n"
        if error_msg:
            print(f"{error_msg}Valid fields are {self.line_obj._fields}", file=sys.stderr)
            sys.exit(1)

    def verify_header(self, line, line_num):
        """Given a 2nd table header, verify the fields match ours in some order."""
        parts = get_line_parts(line)
        error_message = ""
        orig_fields = set(self.line_obj._fields)
        new_fields = set(parts)
        if new_fields - orig_fields:
            error_message = f"{error_message}There are additional unknown fields at line {line_num}: {sorted(list(new_fields - orig_fields))}\n"
        if orig_fields - new_fields:
            error_message = f"{error_message}There are missing fields at line {line_num}: {sorted(list(orig_fields - new_fields))}\n"
        if error_message:
            print(error_message, file=sys.stderr)
            sys.exit(1)

    def add_line(self, line):
        """Add a line or lines, depending on split_column."""
        orig_parts = get_line_parts(line, self.split_column)
        if self.split_column:
            splits = {}
            for key in self.split_column:
                splits[key] = orig_parts[key]
            for partial_parts in zip_longest(*list(splits.values()), fillvalue=""):
                new_parts = orig_parts[:]
                for key, val in zip(self.split_column, partial_parts):
                    new_parts[key] = val
                self.do_add_line(new_parts)
        else:
            self.do_add_line(orig_parts)

    def do_add_line(self, parts):
        """Add a line"""
        line_obj = self.line_obj(*parts)
        if self.column:
            key = parts[self.column]
            self.column_values.add(key)
            self.parsed_lines.setdefault(key, []).append(line_obj)
        self.update_max_width([len(x) for x in parts])
        self.line_count += 1

    def update_max_width(self, widths):
        """Update self.max_width with any wider width"""
        for count, value in enumerate(widths):
            if value > self.max_width[count]:
                self.max_width[count] = value


def _outline_to_yaml(line):
    """Return the outline string yaml-ified."""
    return line.strip('"').replace("[[", "").replace("]]", "").replace('"', "").replace(":", " -")


def get_line_parts(line, split_column=None):
    """Split a markdown table by pipes, return the list and their widths"""
    line = line.strip()
    parts = []
    for i, part in enumerate(line.strip("|").split("|")):
        part = part.strip()
        if split_column and i in split_column:
            part = [x.strip() for x in part.split(",")]
        parts.append(part)
    return parts


def get_outline_file_header(beats_type):
    tags = {"outline", beats_type.lower()}
    return f"""---
tags: {sorted(list(tags))}
aliases: []
---

# {beats_type.capitalize()}

"""


def get_beats(
    table,
    filter=None,
    file_headers=False,
    multi_table_output=False,
    stats=False,
    format_=None,
    beats_type="outline",
):
    """Return the output."""
    stdout = ""
    stderr = ""
    if file_headers:
        # TODO read header from original file; otherwise set tags and aliases to []
        stdout += get_outline_file_header(beats_type)

    if format_ == "yaml":
        stdout = f"{stdout}{get_yaml_from_table(table, _filter=filter)}"
    elif format_ is None or format_ == "markdown":
        stdout = f"{stdout}{get_markdown_from_table(table, _filter=filter, multi_table=multi_table_output)}"
    elif format_ == "html":
        # No markdown file headers in html
        stdout = get_html_from_table(table, _filter=filter, multi_table=multi_table_output)
    else:
        raise Exception(f"Unknown format {format_}!")

    if stats:
        if table.column_values:
            values = set()
            if filter:
                for val in table.column_values:
                    values.update(set(split_by_char(val, "/")))
                values = list(values)
            else:
                values = table.column_values
            stderr = f"{stderr}Num values: {len(values)} {sorted(values)}\n"
        stderr = f"{stderr}Num beats: {table.line_count}"
    return stdout, stderr


def build_table_from_file(path, column=None, order=None, split_column=None, target_table_num=None):
    """Parse the given filehandle's table(s)."""
    in_table = False
    cur_table_num = 0
    line_num = 0
    table = None
    with open(path) as fh:
        for line in fh:
            line_num += 1
            if not in_table:
                if line.startswith("|"):
                    in_table = True
                    cur_table_num += 1
                    if target_table_num is not None and cur_table_num != target_table_num:
                        continue
                    if table is None:
                        table = Table(
                            line,
                            column=column,
                            order=order,
                            split_column=split_column,
                        )
                    else:
                        table.verify_header(line, line_num)
                continue
            if not line.startswith("|"):
                in_table = False
                continue
            if target_table_num is not None and cur_table_num != target_table_num:
                continue
            if TABLE_DIVIDER_REGEX.match(line):
                continue
            if table is not None:
                table.add_line(line)
    return table


def get_markdown_table_header(header):
    """Return the table header and divider line"""
    return f'{header}\n{re.sub(r"""[^+|]""", "-", header)}'


def header_text_to_header_anchor(header_text):
    """Munge the header_text into a header anchor:

    - All text is converted to lowercase.
    - All non-word text (e.g., punctuation, HTML) is removed.
    - All spaces are converted to hyphens.
    - Two or more hyphens in a row are converted to one.
    - If a header with the same ID has already been generated, a unique incrementing number is appended, starting at 1.
    """
    anchor = header_text.lower()
    anchor = re.sub(SPECIAL_CHAR_REGEX, "", anchor)
    anchor = anchor.replace(" ", "-")
    anchor = re.sub("-+", "-", anchor)
    return anchor


def get_markdown_from_table(table, _filter=None, multi_table=False):
    """Return all the appropriate lines in markdown format."""
    widths = dict(zip(list(table.line_obj._fields), table.max_width))
    header = "|"
    for o in table.order:
        header += f" {{:<{widths[o]}}} |".format(o)
    toc = ""
    body = ""
    if not multi_table:
        body = f"{body}{get_markdown_table_header(header)}\n"
    for k, v in sorted(table.parsed_lines.items()):
        if _filter:
            filter_key = split_by_char(k, "/")
            if set(filter_key).isdisjoint(set(_filter)):
                continue
        if multi_table:
            body = f"{body}\n## {k}\n{get_markdown_table_header(header)}\n"
            toc = (
                f"{toc}- {k} [github](#{header_text_to_header_anchor(k)}) [obsidian](#{quote(k)})\n"
            )
        for line in v:
            output = "|"
            for o in table.order:
                output += f" {{:<{widths[o]}}} |".format(getattr(line, o))
            body = f"{body}{output}\n"
    return f"{toc}{body}"


def get_yaml_from_table(table, _filter=None):
    """Return all the appropriate lines in yaml format."""
    yaml_output = ""
    for k, v in sorted(table.parsed_lines.items()):
        if _filter and set(split_by_char(k, "/")).isdisjoint(set(_filter)):
            continue
        for line in v:
            output = _outline_to_yaml(line.Description)
            if line.Beat:
                arcs = line.Arc.split(",")
                beats = line.Beat.split(",")
                arc_beats = []
                for arc_beats_tuple in zip_longest(arcs, beats, fillvalue=""):
                    arc_beats.append(" ".join(arc_beats_tuple).strip())
                output = f"""- {output} ({", ".join(arc_beats)})\n"""
            else:
                output = f"- {output} ({line.Arc})\n"
            yaml_output = f"{yaml_output}{output}"
    return yaml_output


def get_html_from_table(table, _filter=None, multi_table=False):
    """Return all the appropriate lines in html format."""
    table_header = "<table><tr>\n"
    for o in table.order:
        table_header = f"{table_header}  <th>{o}</th>\n"
    table_header = f"{table_header}</tr>"
    body = OUTLINE_HTML_HEADER
    if not multi_table:
        body = f"{body}{table_header}\n"
    for k, v in sorted(table.parsed_lines.items()):
        if _filter:
            filter_key = split_by_char(k, "/")
            if set(filter_key).isdisjoint(set(_filter)):
                continue
        if multi_table:
            body = f"{body}\n<h2>{k}</h2>\n{table_header}\n"

        for line in v:
            output = "<tr>\n"
            for o in table.order:
                output = f"{output}  <td>{re.sub(r""" - """, "&mdash;", getattr(line, o))}</td>\n"
            body = f"{body}{output}</tr>\n"
        body = f"{body}</table>\n"
    body = f"{body}</body></html>\n"
    return body
