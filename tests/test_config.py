"""Test constants."""

from pathlib import Path

import markdown_novel_tools.config as mdconfig


def test_get_primary_outline_path():
    config = {
        "outline": {"outline_dir": "/tmp", "primary_outline_file": "foo"},
    }
    expected = Path("/tmp/foo")
    assert mdconfig.get_primary_outline_path(config) == expected
