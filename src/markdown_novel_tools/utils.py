#!/usr/bin/env python3
"""markdown-novel-tools utils."""

import datetime
import os
from pathlib import Path

import pytz
import yaml

from markdown_novel_tools.constants import TIMEZONE


# Don't print `null` for None in yaml strings
def represent_none(self, _):
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)


def find_markdown_files(paths):
    """Return a list of markdown files in base_path."""

    if isinstance(paths, str):
        paths = [paths]

    file_paths = []
    for base_path in paths:
        if os.path.isfile(base_path):
            file_paths.append(base_path)
            continue
        root = Path(base_path)

        for root, dirs, files in os.walk(root):
            for file_ in sorted(files):
                if file_.endswith(".md"):
                    path = os.path.join(root, file_)
                    file_paths.append(path)
    return file_paths


def local_time(timestamp):
    utc_tz = pytz.utc
    local_tz = pytz.timezone(TIMEZONE)
    utc_dt = datetime.datetime.fromtimestamp(timestamp, utc_tz)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


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
