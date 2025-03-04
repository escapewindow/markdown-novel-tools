#!/usr/bin/env python3
"""markdown-novel-tools utils."""

import datetime

import pytz
import yaml

from markdown_novel_tools.constants import TIMEZONE


# Don't print `null` for None in yaml strings
def represent_none(self, _):
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)


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
    )
