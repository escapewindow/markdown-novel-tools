#!/usr/bin/env python3
"""markdown-novel-tools utils."""

import datetime
import os
import subprocess
from difflib import unified_diff
from pathlib import Path
from shutil import which

import pytz
import yaml

from markdown_novel_tools.constants import TIMEZONE


def represent_none(self, _):
    """Don't print `null` for None in yaml strings."""
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)


def diff_yaml(from_yaml, to_yaml, from_name="from", to_name="to", verbose=False):
    """Diff outline and scene yaml strings."""
    if verbose:
        print(from_yaml, end="")
        print(to_yaml, end="")

    diff = ""
    for line in unified_diff(
        from_yaml.splitlines(), to_yaml.splitlines(), fromfile=from_name, tofile=to_name
    ):
        diff = f"{diff}{line.rstrip()}\n"

    return diff


def find_files_by_content(_from):
    """A recursive grep."""
    files = []
    try:
        output = subprocess.check_output(["rg", "-F", "-l", _from])
        for i in output.splitlines():
            files.append(i.decode("utf-8"))
    except subprocess.CalledProcessError:
        pass
    return files


def find_files_by_name(_from):
    """Find files by name.

    TODO:
    - should this include non-markdown?
    - exclude kwarg to remove "snippets" hardcode?
    - should we combine this and `find_markdown_files`?
    """
    files = []
    try:
        output = subprocess.check_output(
            ["fd", "-s", "-F", "-E", "snippets", _from]
        )  # TODO unhardcode
        for i in output.splitlines():
            files.append(i.decode("utf-8"))
    except subprocess.CalledProcessError:
        pass
    return files


def find_markdown_files(paths):
    """Return a list of markdown files in `paths`."""

    if isinstance(paths, str):
        paths = [paths]

    file_paths = []
    for base_path in paths:
        if os.path.isfile(base_path):
            file_paths.append(base_path)
            continue
        root = Path(base_path)

        for root, _, files in os.walk(root):
            for file_ in sorted(files):
                if file_.endswith(".md"):
                    path = os.path.join(root, file_)
                    file_paths.append(path)
    return file_paths


def local_time(timestamp):
    """Get the local datetime for a given timestamp."""
    utc_tz = pytz.utc
    local_tz = pytz.timezone(TIMEZONE)
    utc_dt = datetime.datetime.fromtimestamp(timestamp, utc_tz)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


def output_diff(diff):
    """Output diff, using `diff-so-fancy` if it exists."""
    if not diff:
        return
    if which("diff-so-fancy"):
        subprocess.run(["diff-so-fancy"], input=diff.encode("utf-8"), check=True)
    else:
        print(diff, end="")


def round_to_one_decimal(f):
    """round float f to 1 decimal place"""
    return f"{f:.1f}"


def unwikilink(string, remove=("[[", "]]", "#")):
    """Remove the [[ ]] from a string. Also # for tags."""
    for repl in remove:
        string = string.replace(repl, "")
    return string


def yaml_string(yaml_object):
    """Return a yaml formatted string from the yaml object."""

    return yaml.dump(
        yaml_object,
        default_flow_style=False,
        width=float("inf"),
        sort_keys=False,
        allow_unicode=True,
    )
