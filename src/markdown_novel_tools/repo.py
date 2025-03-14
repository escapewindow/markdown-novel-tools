#!/usr/bin/env python3
"""Repo related functions."""

import argparse
import os
import platform
import subprocess
import time
from pathlib import Path

from git import Repo

from markdown_novel_tools.utils import find_files_by_content, find_files_by_name, local_time


def num_commits_today():
    """Print the number of git commits in cwd today."""
    path = Path(os.getcwd())
    repo = Repo(path)
    time_fmt = "%Y%m%d"
    todays_date = local_time(time.time()).strftime(time_fmt)
    # current_commit = repo.head.commit
    # current_commit_date = local_time(current_commit.committed_date).strftime(time_fmt)
    count = 0
    for rev in repo.iter_commits(repo.head.ref):
        if local_time(rev.committed_date).strftime(time_fmt) != todays_date:
            break
        count += 1
    return count


def replace():
    """Replace strings in filenames and files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    parser.add_argument("from_")
    parser.add_argument("to")
    opts = parser.parse_args()
    content_files = find_files_by_content(opts.from_)
    print("\n".join(content_files))
    if not opts.list:
        if platform.system() == "Darwin":
            sed = "gsed"
        else:
            sed = "sed"
        for _file in content_files:
            subprocess.check_call([sed, "-e", f"s%{opts.from_}%{opts.to}%g", "-i", _file])
    name_files = find_files_by_name(opts.from_)
    print("\n".join(name_files))
    if not opts.list:
        for _file in name_files:
            to_file = _file.replace(opts.from_, opts.to)
            subprocess.check_call(["git", "mv", _file, to_file])
