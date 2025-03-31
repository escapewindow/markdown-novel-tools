#!/usr/bin/env python3
"""markdown-novel-tools config."""

import os
from pathlib import Path

import yaml
from git import InvalidGitRepositoryError, Repo


def get_config_path():
    """Search the usual suspect paths for the config file and return it."""
    search_path = []

    try:
        git_repo = Repo(Path("."), search_parent_directories=True)
        git_root = Path(git_repo.git.rev_parse("--show-toplevel"))
        search_path.append(git_root / ".config.yaml")
    except InvalidGitRepositoryError:
        pass
    if "XDG_CONFIG_HOME" in os.environ:
        search_path.append(Path(os.environ["XDG_CONFIG_HOME"]) / "md-novel" / "novel-config.yaml")
    search_path.append(Path(os.environ["HOME"]) / ".novel_config.yaml")
    for path in search_path:
        if os.path.exists(path):
            return path


def get_primary_outline_path(config):
    """Return the primary outline path."""
    return Path(config["outline_dir"]) / config["primary_outline_file"]


def get_config():
    """Read and return the config."""
    config = {}
    path = get_config_path()
    if path is not None:
        with open(path) as fh:
            config = yaml.safe_load(fh)
    return config
