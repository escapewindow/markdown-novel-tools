"""manuscript-novel-tools setup.py."""

import datetime
import os
from pathlib import Path

from setuptools import setup

project_dir = Path(os.path.abspath(os.path.dirname(__file__)))
os.chdir(project_dir)

# Using CalVer https://calver.org/
VERSION = datetime.date.today().strftime("%y.%m.%d")

tests_require = [
    "flake8",
    "flake8_docstrings",
    "pytest",
]

with open(project_dir / "requirements.txt") as f:
    install_requires = f.readlines()

with open(project_dir / "README.md") as fh:
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
            "parse_beats = markdown_novel_tools.outline:parse_beats",
            "manuscript_stats = markdown_novel_tools.scene:stats",
            "frontmatter_tool = markdown_novel_tools.manuscript:frontmatter_tool",
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
