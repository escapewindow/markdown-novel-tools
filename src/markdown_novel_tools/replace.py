#!/usr/bin/env python
import argparse
import platform
import subprocess
import sys


def find_files_by_content(_from):
    files = []
    try:
        output = subprocess.check_output(["rg", "-F", "-l", _from])
        for i in output.splitlines():
            files.append(i.decode("utf-8"))
    except subprocess.CalledProcessError:
        pass
    return files


def find_files_by_name(_from):
    files = []
    try:
        output = subprocess.check_output(["fd", "-s", "-F", "-E", "snippets", _from])
        for i in output.splitlines():
            files.append(i.decode("utf-8"))
    except subprocess.CalledProcessError:
        pass
    return files


def replace():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", action=argparse.BooleanOptionalAction)
    parser.add_argument("_from")
    parser.add_argument("to")
    opts = parser.parse_args()
    content_files = find_files_by_content(opts._from)
    print("\n".join(content_files))
    if not opts.list:
        if platform.system() == "Darwin":
            sed = "gsed"
        else:
            sed = "sed"
        for _file in content_files:
            subprocess.check_call([sed, "-e", f"s%{opts._from}%{opts.to}%g", "-i", _file])
    name_files = find_files_by_name(opts._from)
    print("\n".join(name_files))
    if not opts.list:
        for _file in name_files:
            to_file = _file.replace(opts._from, opts.to)
            subprocess.check_call(["git", "mv", _file, to_file])
