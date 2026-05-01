"""Test constants."""

import os
import re
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from git import Repo

import markdown_novel_tools.config as mdconfig


def hack_private_var(path):
    """Mac /private/var is /var, but git.Repo returns one and Path returns the other"""
    return re.sub("^/private/var/", "/var/", str(path))


def test_get_config_path():
    with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp_repo, tempfile.TemporaryDirectory() as tmp_config:
        os.environ = {
            "HOME": tmp_home,
            "XDG_CONFIG_HOME": tmp_config,
        }
        os.chdir(tmp_repo)

        # No config file in invalid git root, config dir, home dir
        assert mdconfig.get_config_path() is None

        # No config file in valid git root, config dir, home dir
        Repo.init(tmp_repo)
        assert mdconfig.get_config_path() is None

        # home config
        home_config = Path(tmp_home) / ".novel_config.yaml"
        home_config.touch()
        assert mdconfig.get_config_path() == home_config

        # config config
        config_config = Path(tmp_config) / "md-novel" / "novel-config.yaml"
        os.mkdir(config_config.parent)
        config_config.touch()
        assert mdconfig.get_config_path() == config_config

        repo_path = Path(tmp_repo)
        os.makedirs(repo_path / "parent" / "child")
        repo_config_path = repo_path / ".config.yaml"
        repo_config_path.touch()
        for path in (repo_path, repo_path / "parent", repo_path / "parent" / "child"):
            os.chdir(path)
            assert hack_private_var(mdconfig.get_config_path()) == hack_private_var(
                repo_config_path
            )


def test_single_book_primary_outline_path():
    config = {
        "outline": {"single": {"primary_outline_file": "/tmp/foo"}},
    }
    expected = Path("/tmp/foo")
    assert mdconfig.single_book_primary_outline_path(config) == expected


@pytest.mark.parametrize(
    "format_, expected",
    (
        ("one", "one_path"),
        ("two", "two_path"),
        (None, "default_path"),
        ("nonexistent", "default_path"),
    ),
)
def test_get_metadata_path(format_, expected):
    config = {
        "convert": {
            "metadata_path": {
                "one": "one_path",
                "two": "two_path",
                "default": "default_path",
            },
        }
    }
    kwargs = {}
    if format_ is not None:
        kwargs["format_"] = format_
    assert mdconfig.get_metadata_path(config, **kwargs) == Path(expected)


@pytest.mark.parametrize(
    "variant, expected, raises",
    (
        (None, "css_dir/pdf_path", None),
        ("manuscript_pdf_css_path", "css_dir/pdf_path", None),
        ("one", "css_dir/one_path", None),
        ("two", "css_dir/two_path", None),
        ("nonexistent", None, KeyError),
    ),
)
def test_get_css_path(variant, expected, raises):
    config = {
        "convert": {
            "css": {
                "css_dir": "css_dir",
                "manuscript_pdf_css_path": "pdf_path",
                "one": "one_path",
                "two": "two_path",
            },
        }
    }
    kwargs = {}
    if variant is not None:
        kwargs["variant"] = variant
    if raises:
        with pytest.raises(raises):
            mdconfig.get_css_path(config, **kwargs)
    else:
        assert mdconfig.get_css_path(config, **kwargs) == Path(expected)


def test_get_markdown_template_choices():
    with tempfile.TemporaryDirectory() as tmpdir:
        expected = ["one", "two", "three"]
        for path in expected:
            Path("/".join([tmpdir, f"{path}.md"])).touch()
        config = {
            "markdown_template_dir": tmpdir,
        }
        assert mdconfig.get_markdown_template_choices(config) == sorted(expected)


@pytest.mark.parametrize(
    "var, repl_dict, expected, raises",
    (
        (set(["a", "b"]), {}, None, TypeError),
        ("same", None, "same", None),
        (None, {}, None, None),
        ("foo{foo}", {"foo": "bar"}, "foobar", None),
        ({"foo": "{foo}"}, {"foo": "bar"}, {"foo": "bar"}, None),
        ({"a": "{foo}", "b": "b{foo}"}, {"foo": "bar"}, {"a": "bar", "b": "bbar"}, None),
        (
            {
                "top": {
                    "a": "{foo}bar",
                    "b": "b{foo}",
                    "c": "c{foo}x",
                    "d": {
                        "e": "e{foo}",
                    },
                },
                "xx": "{foo}bar",
            },
            {"foo": "bar"},
            {
                "top": {
                    "a": "barbar",
                    "b": "bbar",
                    "c": "cbarx",
                    "d": {
                        "e": "ebar",
                    },
                },
                "xx": "barbar",
            },
            None,
        ),
    ),
)
def test_replace_values(var, repl_dict, expected, raises):
    if raises:
        with pytest.raises(raises):
            mdconfig._replace_values(var, repl_dict)
    else:
        assert mdconfig._replace_values(var, repl_dict) == expected


@pytest.mark.parametrize(
    "config_val, user_config_val, key_name, use_default_keys, repl_dict, raises, expected",
    (
        # Simple string fallthrough
        ("a", None, "", True, {}, None, "a"),
        # User string override
        ("a", "b", "", True, {}, None, "b"),
        # User list override
        (["a"], ["b", "c"], "", True, {}, None, ["b", "c"]),
        #
        ## Combined user and default config dicts
        ##
        ## override an existing key, use_default_keys=True
        ({"a": "foo", "b": "bar"}, {"a": "baz"}, "", True, {}, None, {"a": "baz", "b": "bar"}),
        ## add a nonexistent value, use_default_keys=True
        ({"a": "foo", "b": "bar"}, {"c": "baz"}, "", True, {}, None, {"a": "foo", "b": "bar"}),
        ## add a nonexistent value, use_default_keys=False
        (
            {"a": "foo", "b": "bar"},
            {"c": "baz"},
            "",
            False,
            {},
            None,
            {"a": "foo", "b": "bar", "c": "baz"},
        ),
        #
        # config_val is None
        (None, {"foo": "{foo}"}, "", True, {}, None, None),
        (None, {"foo": "{foo}"}, "", False, {"foo": "bar"}, None, {"foo": "bar"}),
        # Mismatched types
        (["a"], {"b": "c"}, None, True, {}, TypeError, None),
        (["a"], {"b": "c"}, "keyname", True, {}, TypeError, None),
        # Unknown type
        (set(["a"]), set(["b"]), "invalid", True, {}, TypeError, None),
    ),
)
def test_get_new_config_val(
    config_val, user_config_val, key_name, use_default_keys, repl_dict, raises, expected
):
    if raises:
        with pytest.raises(raises):
            mdconfig._get_new_config_val(config_val, user_config_val, key_name)
    else:
        assert (
            mdconfig._get_new_config_val(
                config_val,
                user_config_val,
                key_name=key_name,
                use_default_keys=use_default_keys,
                repl_dict=repl_dict,
            )
            == expected
        )


def test_add_config_parser_args():
    parser = Mock()
    mdconfig.add_config_parser_args(parser)
    parser.add_argument.assert_called()
