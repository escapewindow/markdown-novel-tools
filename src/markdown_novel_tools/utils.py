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
from git import Repo


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


def find_files_by_content(config, _from):
    """A recursive grep."""
    files = []
    try:
        output = subprocess.check_output(config["find_files_by_content_cmd"] + [_from])
        for i in output.splitlines():
            files.append(i.decode("utf-8"))
    except subprocess.CalledProcessError:
        pass
    return files


def find_files_by_name(config, _from):
    """Find files by name.

    TODO:
    - should this include non-markdown?
    - should we combine this and `find_markdown_files`?
    """
    files = []
    try:
        output = subprocess.check_output(config["find_files_by_name_cmd"] + [_from])
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

        for root, dirs, files in os.walk(root):
            for file_ in sorted(files):
                if file_.endswith(".md"):
                    path = os.path.join(root, file_)
                    file_paths.append(path)
            for skip in (".git", ".obsidian"):
                if skip in dirs:
                    dirs.remove(skip)
            for dir in dirs:
                if dir.startswith("_"):
                    dirs.remove(dir)
    return file_paths


def get_git_revision():
    """Get the git revision of a repo."""
    repo = Repo(Path("."), search_parent_directories=True)
    rev = str(repo.head.commit)[0:12]
    if repo.is_dirty():
        rev = f"{rev}+"
    return rev


def local_time(timestamp, timezone="US/Mountain"):
    """Get the local datetime for a given timestamp."""
    utc_tz = pytz.utc
    local_tz = pytz.timezone(timezone)
    utc_dt = datetime.datetime.fromtimestamp(timestamp, utc_tz)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


def mkdir(path, parents=True, exist_ok=True, clean=False):
    """Create a directory, cleaning it first if requested."""
    path = Path(args.path)
    if clean and os.path.exists(path):
        shutil.rmtree(path)
        exist_ok = False
    if not os.path.exists(path):
        path.mkdir(parents=parents, exist_ok=exist_ok)


def output_diff(diff):
    """Output diff, using `diff-so-fancy` if it exists."""
    if not diff:
        return
    if which("diff-so-fancy"):
        subprocess.run(["diff-so-fancy"], input=diff.encode("utf-8"), check=True)
    else:
        print(diff, end="")


def print_object_one_line_per(obj, padding=""):
    """Print a dict, list, or str, one line per val"""
    if isinstance(obj, str):
        print(f"{padding}{str}")
    elif isinstance(obj, (list, tuple)):
        for i in obj:
            print(f"{padding}{i}")
    elif isinstance(obj, dict):
        for key in obj.keys():
            print(f"{padding}{key}")
            print_object_one_line_per(obj[key], f"    {padding}")
    else:
        raise SyntaxError(f"Unknown type of {type(obj)} in print_object_one_line_per!")


def round_to_one_decimal(f):
    """round float f to 1 decimal place"""
    return f"{f:.1f}"


def split_by_char(var, char="/"):
    """Split a line by a character."""
    return_val = None
    if isinstance(var, str):
        return_val = var.split(char)
    elif isinstance(var, (list, tuple)):
        new_var = []
        for i in var:
            new_var.extend(i.split(char))
        return_val = new_var
    else:
        raise TypeError(f"split_by_char: Unknown var type {type(var)}!")
    return return_val


def write_to_file(path, contents):
    with open(path, "w") as fh:
        fh.write(contents)


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
