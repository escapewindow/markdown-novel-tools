#!/usr/bin/env python3

import glob
import os
import subprocess
import tempfile
from pathlib import Path

from git import Repo

from markdown_novel_tools.convert import convert_chapter


def shunn_docx(args):
    """Convert markdown file(s) to a Shunn novel docx suitable for submission to an editor"""
    repo_path = args.config["convert"]["shunn_repo_path"]
    artifact_dir = Path(args.artifact_dir)
    to = artifact_dir / "output.docx"

    convert_chapter(args)

    with tempfile.TemporaryDirectory() as d:
        if repo_path is None:
            repo_path = Path(d) / "repo"
            print(d)
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
