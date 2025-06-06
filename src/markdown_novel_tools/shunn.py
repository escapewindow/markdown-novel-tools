#!/usr/bin/env python3
"""Convert between markdown and editor-submission formatted docx."""

import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo

from markdown_novel_tools.convert import convert_chapter, get_output_basestr


def shunn_docx(args):
    """Convert markdown file(s) to a Shunn novel docx suitable for submission to an editor"""
    repo_path = args.config["convert"]["shunn_repo_path"]
    artifact_dir = Path(args.artifact_dir)
    output_basestr = get_output_basestr(args)
    to = artifact_dir / f"{output_basestr}.docx"

    convert_chapter(args, output_basestr=output_basestr)

    with tempfile.TemporaryDirectory() as d:
        if repo_path is None:
            repo_path = Path(d) / "repo"
            Repo.clone_from(url=args.config["convert"]["shunn_repo_url"], to_path=repo_path)
        else:
            repo_path = Path(os.path.expanduser(repo_path))
        cmd = [
            repo_path / "bin" / "md2long.sh",
            "--output",
            to,
            "--overwrite",
            "--modern",
        ]
        cmd.extend(sorted(artifact_dir.glob("*.md")))
        subprocess.check_call(cmd)


def shunn_md(args):
    """Convert a docx file to markdown files."""
    artifact_dir = Path(args.artifact_dir)
    if args.clean and os.path.exists(artifact_dir):
        shutil.rmtree(artifact_dir)
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)

    with tempfile.TemporaryDirectory() as d:
        tmpfile = Path(d) / "temp.md"
        cmd = [
            "pandoc",
            "--from=docx",
            "--to=markdown_strict",
            "--columns=80",
            f"--output={tmpfile}",
            args.filename[0],
        ]
        subprocess.check_call(cmd)

        with open(tmpfile) as from_fh:
            count = 1
            contents = ""
            for line in from_fh.readlines():
                if line.startswith("# ") and contents:
                    with open(artifact_dir / f"chapter{str(count).zfill(3)}.md", "w") as fh:
                        fh.write(contents)
                    contents = ""
                    count += 1
                contents += line
            with open(artifact_dir / f"chapter{str(count).zfill(3)}.md", "w") as fh:
                fh.write(contents)
