#!/usr/bin/env python3
"""markdown-novel-tools config."""

import argparse
import glob
import os
from copy import deepcopy
from pathlib import Path

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


def get_markdown_template_choices(config):
    """List the markdown template choices available."""
    template_dir = Path(config["markdown_template_dir"])
    choices = []
    for file in glob.glob(str(template_dir / "*.md")):
        choices.append(os.path.basename(file).replace(".md", ""))
    return sorted(choices)


def _replace_values(var, repl_dict):
    """Replace values in a string, or recursively in a list or dict"""
    if repl_dict is None or var is None:
        return_val = var
    elif isinstance(var, str):
        return_val = var.format(**repl_dict)
    elif isinstance(var, (list, tuple)):
        new_var = []
        for i in var:
            new_var.append(_replace_values(i, repl_dict))
        return_val = new_var
    elif isinstance(var, dict):
        new_var = {}
        for k, v in var.items():
            new_var[k] = _replace_values(v, repl_dict)
        return_val = new_var
    else:
        raise TypeError(f"_replace_values: Unknown var type {type(var)}!")
    return return_val


def _get_new_config_val(
    config_val, user_config_val, key_name=None, use_default_keys=True, repl_dict=None
):
    """Return the new config val"""
    repl_dict = repl_dict or {}
    if user_config_val is None:
        return _replace_values(config_val, repl_dict)
    if config_val is None:
        return
    if type(config_val) is not type(user_config_val):
        error = f"{type(user_config_val)} is not {type(config_val)}!"
        if key_name is not None:
            error = f"{error} for config key {key_name}!"
        raise TypeError(error)
    if isinstance(config_val, (str, list)):
        return _replace_values(user_config_val, repl_dict)
    if isinstance(config_val, dict):
        if use_default_keys:
            from_dict = config_val
        else:
            from_dict = user_config_val
        for key in from_dict:
            if key in user_config_val:
                config_val[key] = _get_new_config_val(
                    config_val.get(key),
                    user_config_val.get(key),
                    key_name=key,
                    use_default_keys=False,
                    repl_dict=repl_dict,
                )
            else:
                config_val[key] = _replace_values(config_val[key], repl_dict)
        return config_val
    raise TypeError(f"Unknown type {type(user_config_val)} in config key {key_name}!")


def add_config_parser_args(parser):
    """Add config parser args; here to fix --help. These can't have required functions."""
    parser.add_argument("-c", "--config-path")
    parser.add_argument("-b", "--book-num")


def get_config():
    """Read and return the config."""
    config_parser = argparse.ArgumentParser(add_help=False)
    add_config_parser_args(config_parser)
    config_args, remaining_args = config_parser.parse_known_args()
    config = deepcopy(DEFAULT_CONFIG)
    path = config_args.config_path or get_config_path()
    user_config = {}
    if path is not None:
        with open(path) as fh:
            user_config = yaml.safe_load(fh)
    book_num = config_args.book_num or user_config.get("book_num", config.get("book_num"))
    repl_dict = {
        "book_num": book_num or "",
    }
    config = _get_new_config_val(config, user_config, repl_dict=repl_dict)
    config.setdefault("book_num", book_num)
    return config, remaining_args
