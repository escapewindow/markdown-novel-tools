"""manuscript-novel-tools setup.py."""

import datetime
import os
from pathlib import Path

from setuptools import setup

project_dir = Path(os.path.abspath(os.path.dirname(__file__)))
os.chdir(project_dir)

VERSION = "0.1"

tests_require = [
    "flake8",
    "flake8_docstrings",
    "pytest",
]

with open(project_dir / "requirements.txt", encoding="utf-8") as f:
    install_requires = f.readlines()

with open(project_dir / "README.md", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name="markdown_novel_tools",
    version=VERSION,
    description="Markdown Novel Tools",
    long_description=long_description,
    author="Aki Sasaki",
    author_email="aki@escapewindow.com",
    url="https://github.com/escapewindow/markdown-novel-tools",
    packages=["markdown_novel_tools"],
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "frontmatter = markdown_novel_tools.manuscript:frontmatter_tool",
            "novel-beats = markdown_novel_tools.outline:parse_beats",
            "novel-convert = markdown_novel_tools.convert:convert",
            "novel-replace = markdown_novel_tools.replace:replace",
            "novel-stats = markdown_novel_tools.scene:stats",
            "novel-today = markdown_novel_tools.manuscript:today",
        ]
    },
    zip_safe=False,
    license="MPL 2.0",
    install_requires=install_requires,
    tests_require=tests_require,
    python_requires=">=3.7",
    classifiers=[
        "Intended Audience :: Other Audience",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
