#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

import argparse
import os
import re
import sys

import yaml

from markdown_novel_tools.config import add_config_parser_args, get_config, get_primary_outline_path
from markdown_novel_tools.constants import MANUSCRIPT_REGEX
from markdown_novel_tools.mdfile import FRONTMATTER_VALIDATOR, get_markdown_file
from markdown_novel_tools.outline import build_table_from_file, get_yaml_from_table
from markdown_novel_tools.utils import (
    diff_yaml,
    find_markdown_files,
    output_diff,
    print_object_one_line_per,
    yaml_string,
)


# Frontmatter {{{1
def frontmatter_check(args):
    """Check frontmatter schema."""

    files = find_markdown_files(args.path)
    for path in files:
        markdown_file = get_markdown_file(path)
        FRONTMATTER_VALIDATOR.validate(markdown_file.parsed_yaml)
        if FRONTMATTER_VALIDATOR.errors:
            print(f"{os.path.basename(path)}\n{FRONTMATTER_VALIDATOR.errors}", file=sys.stderr)
            if args.strict:
                sys.exit(1)


def frontmatter_diff(args):
    """Diff frontmatter."""

    if not args.outline:
        args.outline = get_primary_outline_path(config)
    files = find_markdown_files(args.path)
    table = build_table_from_file(args.outline, column="Scene")

    # Diff summaries
    for path in files:
        m = MANUSCRIPT_REGEX.match(os.path.basename(path))
        if not m:
            continue

        outline_summary = get_yaml_from_table(
            table, _filter=[f"{m['chapter_num']}.{m['scene_num']}"]
        )

        markdown_file = get_markdown_file(path)
        scene_summary = yaml_string(markdown_file.parsed_yaml["summary"])

        base_filename = re.sub(r"\.md$", "", os.path.basename(path))
        diff = diff_yaml(
            scene_summary,
            outline_summary,
            from_name=f"{base_filename} scene",
            to_name=f"{base_filename} outline",
            verbose=False,
        )
        output_diff(diff)


def _write_updated_frontmatter(path, markdown_file):
    """Helper function to update the frontmatter of a markdown file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            f"""---
{yaml_string(markdown_file.parsed_yaml).rstrip()}
---
{markdown_file.body}"""
        )


def _fix_frontmatter(old_frontmatter):
    """Fix frontmatter.

    This is a hardcode-heavy function, and is largely here to convert from one schema to another.
    """
    new_frontmatter = {}
    for key in (
        "title",
        "tags",
        "aliases",
        "locations",
        "characters",
        "pov",
        "hook",
        "cliffhanger",
        "summary",
    ):
        new_frontmatter[key] = old_frontmatter.get(key)
    return new_frontmatter


def frontmatter_update(args):
    """Overwrite frontmatter with formatted output after replacing the summary."""

    files = find_markdown_files(args.path)
    table = build_table_from_file(args.outline, column="Scene")

    # Update summaries
    for path in files:
        m = MANUSCRIPT_REGEX.match(os.path.basename(path))
        if not m:
            continue

        outline_summary = yaml.safe_load(
            get_yaml_from_table(table, _filter=[f"{m['chapter_num']}.{m['scene_num']}"])
        )

        markdown_file = get_markdown_file(path)
        if args.fix:
            markdown_file.parsed_yaml = _fix_frontmatter(markdown_file.parsed_yaml)
        markdown_file.parsed_yaml["summary"] = outline_summary
        new_yaml = yaml_string(markdown_file.parsed_yaml).rstrip()

        if args.noop:
            base_filename = re.sub(r"\.md$", "", os.path.basename(path))
            diff = diff_yaml(
                markdown_file.yaml,
                new_yaml,
                from_name=f"{base_filename} orig frontmatter",
                to_name=f"{base_filename} new frontmatter",
            )
            output_diff(diff)
        else:
            _write_updated_frontmatter(path, markdown_file)

    frontmatter_check(args)


def frontmatter_query(args):
    """Query frontmatter."""
    files = find_markdown_files(args.path)

    paths_to_values = {}
    values_to_paths = {}
    # Diff summaries
    for path in files:
        markdown_file = get_markdown_file(path)
        if not isinstance(markdown_file.parsed_yaml, dict):
            if args.verbose:
                print(f"{path} doesn't have yaml; skipping.")
            continue
        values = markdown_file.parsed_yaml.get(args.field, [])
        if isinstance(values, str):
            values = [values]
        if args.grep and args.grep not in values:
            continue
        paths_to_values[path] = values
        for val in values:
            values_to_paths.setdefault(val, []).append(path)

    if args.grep:
        if args.verbose:
            print_object_one_line_per(dict(sorted(paths_to_values.items())))
        else:
            print_object_one_line_per(sorted(paths_to_values.keys()))
        sys.exit()

    if args.aggregate:
        if args.verbose:
            print_object_one_line_per(dict(sorted(values_to_paths.items())))
        else:
            print_object_one_line_per(sorted(values_to_paths.keys()))
        sys.exit()

    print_object_one_line_per(dict(sorted(paths_to_values.items())))


def frontmatter_parser():
    """Return a parser for the frontmatter tool."""
    config, remaining_args = get_config()
    parser = argparse.ArgumentParser(prog="frontmatter")
    parser.add_argument("-s", "--strict", action="store_true")
    parser = add_config_parser_args(
        parser
    )  # these args will be swallowed by the config_parser, but add for --help
    parser.set_defaults(config=config)
    subparsers = parser.add_subparsers()

    # frontmatter check
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("path", nargs="+")
    check_parser.set_defaults(func=frontmatter_check)

    # frontmatter diff
    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("-o", "--outline", default=get_primary_outline_path(config))
    diff_parser.add_argument("path", nargs="+")
    diff_parser.set_defaults(func=frontmatter_diff)

    # frontmatter query
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("-f", "--field", required=True)
    query_parser.add_argument("-g", "--grep")
    query_parser.add_argument(
        "-a",
        "--aggregate",
        action="store_true",
        help="Print a sorted set of values. Must be used with `--field`.",
    )
    query_parser.add_argument("-v", "--verbose", action="store_true")
    query_parser.add_argument("path", nargs="+")
    query_parser.set_defaults(func=frontmatter_query)

    # frontmatter update
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("-f", "--fix", action="store_true")
    update_parser.add_argument("-n", "--noop", action="store_true")
    update_parser.add_argument("-o", "--outline", default=get_primary_outline_path(config))
    update_parser.add_argument("path", nargs="+")
    update_parser.set_defaults(func=frontmatter_update)

    return parser, remaining_args


def frontmatter_tool():
    """Work on summaries in both the outline and scene(s)."""

    parser, remaining_args = frontmatter_parser()
    args = parser.parse_args(remaining_args)
    args.func(args)
