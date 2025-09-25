"""Test constants."""

from pathlib import Path

import pytest
from git import Repo

import markdown_novel_tools.config as mdconfig


def test_get_config_path():
    """
    TODO
    - set XDG_CONFIG_HOME and HOME to empty/nonexistent dirs, make sure return value is None
    - create bogus git repo with a .config.yaml, cd into there, make sure we get that
    - set XDG_CONFIG_HOME to a dir with a .config.yaml, make sure we get that
    - set HOME to that dir, make sure we get that
    - set all of them, make sure we get the git one

    Do I want a git repo for any other tests? I could create a bogus one as a fixture
    """


#    try:
#        git_repo = Repo(Path("."), search_parent_directories=True)
#        git_root = Path(git_repo.git.rev_parse("--show-toplevel"))
#        search_path.append(git_root / ".config.yaml")
#    except InvalidGitRepositoryError:
#        pass
#    if "XDG_CONFIG_HOME" in os.environ:
#        search_path.append(Path(os.environ["XDG_CONFIG_HOME"]) / "md-novel" / "novel-config.yaml")
#    search_path.append(Path(os.environ["HOME"]) / ".novel_config.yaml")
#    for path in search_path:
#        if os.path.exists(path):
#            return path


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
