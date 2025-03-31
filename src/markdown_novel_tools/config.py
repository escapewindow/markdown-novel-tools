#!/usr/bin/env python3
"""markdown-novel-tools config."""

import os
from pathlib import Path

import toml
from git import InvalidGitRepositoryError, Repo


def get_config_path(args):
    """Search the usual suspect paths for the config file and return it."""
    search_path = []
    if args.config_path:
        search_path.append(args.config_path)
    search_path.append(Path(".") / ".config.toml")

    try:
        git_repo = Repo(Path("."), search_parent_directories=True)
        git_root = Path(git_repo.git.rev_parse("--show-toplevel"))
        search_path.append(git_root / ".config.toml")
    except InvalidGitRepositoryError:
        pass
    search_path.append(Path(os.environ["HOME"]) / ".novel_config.toml")
    for path in search_path:
        if os.path.exists(path):
            return path


def get_primary_outline_path(config):
    """Return the primary outline path."""
    return Path(config["outline"]["outline_dir"]) / config["outline"]["primary"]["path"]


def get_config(args):
    """Read and return the config."""
    config = {}
    path = get_config_path(args)
    if path is not None:
        config = toml.load(path)
    return config
