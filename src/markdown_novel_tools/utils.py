#!/usr/bin/env python3
"""markdown-novel-tools utils."""


def round_to_one_decimal(f):
    """round float f to 1 decimal place"""
    return f"{f:.1f}"


def unwikilink(string, remove=("[[", "]]", "#")):
    """Remove the [[ ]] from a string. Also # for tags."""
    for repl in remove:
        string = string.replace(repl, "")
    return string
