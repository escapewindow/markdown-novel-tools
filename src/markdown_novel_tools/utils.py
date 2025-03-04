#!/usr/bin/env python3
"""markdown-novel-tools utils."""

import datetime

import pytz

from markdown_novel_tools.constants import TIMEZONE


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
