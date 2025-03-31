#!/usr/bin/env python3
"""Manuscript - cross-outline and -scene."""

import argparse
import os
import re
import sys

import yaml

from markdown_novel_tools.constants import MANUSCRIPT_RE
from markdown_novel_tools.outline import do_parse_file
from markdown_novel_tools.scene import FRONTMATTER_VALIDATOR, get_markdown_file
from markdown_novel_tools.utils import diff_yaml, find_markdown_files, output_diff, yaml_string


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


def frontmatter_fix(args):
    """Fix frontmatter.

    This is a hardcode-heavy function, and is largely here to convert from one schema to another.
    """
    files = find_markdown_files(args.path)
    for path in files:
        markdown_file = get_markdown_file(path)
        old = markdown_file.parsed_yaml
        new = {}
        for key in (
            "Title",
            "tags",
            "aliases",
            "Locations",
            "Characters",
            "POV",
            "Hook",
            "Scene",
            "Sequel",
            "Cliffhanger",
            "Summary",
        ):
            new[key] = old.get(key)
        if "Location" in old:
            if isinstance(old["Location"], list):
                new["Locations"] = old["Location"]
            else:
                new["Locations"] = [old["Location"]]
        for key in ("Scene", "Sequel"):
            if isinstance(new[key], list):
                new[key] = {}
                for val in old[key]:
                    new[key].update(val)
        if old.get("Ideas / thoughts / todo"):
            new["Ideas / thoughts / todo"] = old["Ideas / thoughts / todo"]
        markdown_file.parsed_yaml = new
        _write_updated_frontmatter(path, markdown_file)


def frontmatter_diff(args):
    """Diff frontmatter."""

    files = find_markdown_files(args.path)
    with open(args.outline, encoding="utf-8") as fh:
        table = do_parse_file(fh, column="Scene")

    # Diff summaries
    # TODO should I combine this with the diff in frontmatter_update
    # to avoid duplicating code?
    for path in files:
        m = MANUSCRIPT_RE.match(os.path.basename(path))
        if not m:
            continue

        outline_summary = table.get_yaml(_filter=[f"{m['chapter_num']}.{m['scene_num']}"])

        markdown_file = get_markdown_file(path)
        scene_summary = yaml_string(markdown_file.parsed_yaml["Summary"])

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


def frontmatter_update(args):
    """Overwrite frontmatter with formatted output after replacing the summary."""

    files = find_markdown_files(args.path)
    with open(args.outline, encoding="utf-8") as fh:
        table = do_parse_file(fh, column="Scene")

    # Update summaries
    for path in files:
        m = MANUSCRIPT_RE.match(os.path.basename(path))
        if not m:
            continue

        outline_summary = yaml.safe_load(
            table.get_yaml(_filter=[f"{m['chapter_num']}.{m['scene_num']}"])
        )

        markdown_file = get_markdown_file(path)
        if markdown_file.parsed_yaml["Summary"] == outline_summary:
            continue
        markdown_file.parsed_yaml["Summary"] = outline_summary
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
    if args.sort and (not args.aggregate or not args.field):
        raise SyntaxError("`--aggregate` and `--field` must both be specified with `--sort`!")
    if args.aggregate and not args.field:
        raise SyntaxError("`--field` must be specified with `--aggregate`!")

    files = find_markdown_files(args.path)

    aggregate = set()
    # Diff summaries
    for path in files:
        markdown_file = get_markdown_file(path)
        if args.field:
            value = markdown_file.parsed_yaml[args.field]
            if args.aggregate:
                if isinstance(value, list):
                    aggregate.update(value)
                else:
                    aggregate.add(value)
            else:
                print(path)
                print(yaml_string(value), end="")
        else:
            print(path)
            print(yaml_string(markdown_file.parsed_yaml), end="")
    if aggregate:
        output = f"{args.field}:\n"
        if args.sort:
            aggregate = sorted(aggregate)
        for item in aggregate:
            output = f"{output}- {item}\n"
        print(output, end="")


def frontmatter_parser():
    """Return a parser for the frontmatter tool."""
    parser = argparse.ArgumentParser(prog="frontmatter")
    parser.add_argument("-v", "--verbose", help="Verbose logging.")
    parser.add_argument("-s", "--strict", action="store_true")
    subparsers = parser.add_subparsers()

    # frontmatter check
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("path", nargs="+")
    check_parser.set_defaults(func=frontmatter_check)

    # frontmatter diff
    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument(
        "-o", "--outline", default="outline/Book 1 outline/scenes.md"
    )  # TODO unhardcode
    diff_parser.add_argument("path", nargs="+")
    diff_parser.set_defaults(func=frontmatter_diff)

    # frontmatter fix
    fix_parser = subparsers.add_parser("fix")
    fix_parser.add_argument("path", nargs="+")
    fix_parser.set_defaults(func=frontmatter_fix)

    # frontmatter query
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("-f", "--field")
    query_parser.add_argument(
        "-a",
        "--aggregate",
        action="store_true",
        help="Print a unique list of values. Must be used with `--field`.",
    )
    query_parser.add_argument(
        "-s",
        "--sort",
        action="store_true",
        help="Sort the unique list of values. Must be used with `--field` and `--aggregate`.",
    )
    query_parser.add_argument("path", nargs="+")
    query_parser.set_defaults(func=frontmatter_query)

    # frontmatter update
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument(
        "-o", "--outline", default="outline/Book 1 outline/scenes.md"
    )  # TODO unhardcode
    update_parser.add_argument("-n", "--noop", action="store_true")
    update_parser.add_argument("path", nargs="+")
    update_parser.set_defaults(func=frontmatter_update)

    return parser


def frontmatter_tool():
    """Work on summaries in both the outline and scene(s)."""

    parser = frontmatter_parser()
    args = parser.parse_args()
    args.func(args)
