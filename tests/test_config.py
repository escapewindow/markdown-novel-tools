"""Test constants."""

from pathlib import Path

import pytest

import markdown_novel_tools.config as mdconfig


def test_get_primary_outline_path():
    config = {
        "outline": {"outline_dir": "/tmp", "primary_outline_file": "foo"},
    }
    expected = Path("/tmp/foo")
    assert mdconfig.get_primary_outline_path(config) == expected


@pytest.mark.parametrize(
    "config_val, user_config_val, key_name, raises, expected",
    (
        ("a", None, "", False, "a"),
        ("a", "b", "", False, "b"),
        (["a"], ["b", "c"], "", False, ["b", "c"]),
        ({"a": "foo", "b": "bar"}, {"a": "baz"}, "", False, {"a": "baz", "b": "bar"}),
    ),
)
def test_get_new_config_val(config_val, user_config_val, key_name, raises, expected):
    if raises:
        with pytest.raises(raises):
            md_config._get_new_config_val(config_val, user_config_val, key_name)
    else:
        assert mdconfig._get_new_config_val(config_val, user_config_val, key_name) == expected
