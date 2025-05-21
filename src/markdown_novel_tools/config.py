#!/usr/bin/env python3
"""markdown-novel-tools config."""

import os
from copy import deepcopy
from pathlib import Path
from pprint import pprint

import yaml
from git import InvalidGitRepositoryError, Repo

from markdown_novel_tools.constants import DEFAULT_CONFIG


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
    return Path(config["outline"]["outline_dir"]) / config["outline"]["primary_outline_file"]


def get_metadata_path(config, format_="default"):
    """Get the `novel convert` metadata path for a given format."""
    return Path(
        config["convert"]["metadata_path"].get(
            format_, config["convert"]["metadata_path"]["default"]
        )
    )


def get_css_path(config, variant="manuscript_pdf_css_path"):
    """Return the css path."""
    return Path(config["convert"]["css"]["css_dir"]) / config["convert"]["css"][variant]


def _get_new_config_val(config_val, user_config_val, key_name, use_default_keys=True):
    """Return the new config val"""
    if user_config_val is None:
        return config_val
    if type(config_val) is not type(user_config_val):
        raise TypeError(
            f"{type(user_config_val)} is not {type(config_val)} for config key {key_name}!"
        )
    if isinstance(config_val, (str, list)):
        return user_config_val
    if isinstance(config_val, dict):
        print(f"{key_name} is a dict")
        if use_default_keys:
            from_dict = config_val
        else:
            from_dict = user_config_val
        for key in from_dict:
            if key in user_config_val:
                if isinstance(from_dict[key], dict):
                    config_val[key] = _get_new_config_val(
                        config_val[key], user_config_val[key], key, use_default_keys=False
                    )
                    print(f"hacking {key} with {config_val[key]}")
                else:
                    config_val[key] = user_config_val[key]
                    print(f"just overwriting {key} with {config_val[key]}")
        print(f"key {key_name} is {config_val}")
        return config_val
    raise TypeError(f"Unknown type {type(user_config_val)} in config key {key_name}!")


def get_config():
    """Read and return the config."""
    config = deepcopy(DEFAULT_CONFIG)
    path = get_config_path()
    print(f"config path {path}")
    user_config = {}
    if path is not None:
        with open(path) as fh:
            user_config = yaml.safe_load(fh)
    print(f"user config:")
    print(pprint(user_config))
    for key, val in config.items():
        config[key] = _get_new_config_val(val, user_config.get(key), key)
    print(f"config:")
    print(pprint(config))
    return config
