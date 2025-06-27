#!/usr/bin/env python3
"""Deal with individual markdown files."""

import os
import re
import time
from copy import deepcopy
from pathlib import Path
from pprint import pprint

import yaml
from cerberus import Validator
from git import InvalidGitRepositoryError, Repo

from markdown_novel_tools.constants import ALPHANUM_REGEX, DEBUG, MANUSCRIPT_REGEX
from markdown_novel_tools.utils import local_time, round_to_one_decimal, unwikilink, yaml_string

# Schema {{{1
FRONTMATTER_SCHEMA = {
    "title": {"type": "string", "empty": False, "required": True},
    "tags": {"type": "list", "schema": {"type": "string"}, "required": True},
    "aliases": {"type": "list", "schema": {"type": "string"}, "required": True},
    "locations": {"type": "list", "schema": {"type": "string", "empty": False}, "required": True},
    "characters": {"type": "list", "schema": {"type": "string", "empty": False}, "required": True},
    "pov": {"type": "string", "empty": False, "required": True},
    "hook": {"type": "string", "empty": False, "required": True},
    "cliffhanger": {"type": "string", "required": True},
    "summary": {
        "type": "list",
        "schema": {"type": "string", "empty": False, "required": True},
        "required": True,
    },
    "todo": {
        "type": "list",
        "schema": {"type": "string"},
        "nullable": True,
    },
}
FRONTMATTER_VALIDATOR = Validator(FRONTMATTER_SCHEMA)


# MarkdownFile {{{1
class MarkdownFile:
    """Object for a markdown file."""

    manuscript_info = None
    yaml = ""
    parsed_yaml = None
    error = None

    def __init__(self, path, contents, hack_yaml):
        self.path = Path(path)
        self.manuscript_info = {
            "manuscript_words": 0,
            "total_words": 0,
            "is_manuscript": "manuscript" in self.path.parts,
        }
        self.manuscript_info["title"] = re.sub(r"""\.md$""", "", os.path.basename(path))
        self.hack_yaml = hack_yaml

        if self.manuscript_info["is_manuscript"]:
            m = MANUSCRIPT_REGEX.match(self.manuscript_info["title"])
            if m:
                for attr in ("book_num", "chapter_num", "scene_num"):
                    self.manuscript_info[attr] = m[attr]

        if DEBUG:
            print(f"{path}: ", end="")

        self.yaml, self.body = get_frontmatter_and_body(contents, hack_yaml=self.hack_yaml)
        self.count_words(self.body)
        self.parse_yaml()

        if DEBUG:
            pprint(vars(self))

    def count_words(self, body):
        """Count the words in a markdown file, skipping the header and any
        symbol-only lines.

        """
        for line in body.splitlines():
            for word in line.split():
                if ALPHANUM_REGEX.search(word):
                    self.manuscript_info["total_words"] += 1
                    if self.manuscript_info["is_manuscript"]:
                        self.manuscript_info["manuscript_words"] += 1
                elif DEBUG:
                    print(f"skipping {word}")

    def parse_yaml(self):
        """Parse the yaml of a scene."""
        try:
            self.parsed_yaml = yaml.safe_load(self.yaml)
        except yaml.YAMLError as e:
            print(str(e))
            self.error = f"### {self.path} yaml is broken.\n{str(e)}\n"
            return
        if self.manuscript_info.get("book_num"):
            if self.parsed_yaml.get("pov"):
                self.manuscript_info["pov"] = self.parsed_yaml["pov"]
            for char in self.parsed_yaml.get("characters", []):
                if self.manuscript_info.get("characters") is None:
                    self.manuscript_info["characters"] = []
                self.manuscript_info["characters"].append(char)


# Book {{{1
class Book:
    """Object for a book, specified by the first digit in the manuscript file's name."""

    manuscript_words = 0
    total_words = 0
    chapters = {}
    scenes = {}
    povs = {}

    def __init__(self, book_num):
        self.book_num = book_num

    def add_scene(self, scene):
        """Add a scene to the book, calculating the stats."""
        self.scenes[scene.manuscript_info["title"]] = {
            "manuscript words": scene.manuscript_info["manuscript_words"],
            "total words": scene.manuscript_info["total_words"],
        }
        chapter_num = scene.manuscript_info["chapter_num"]
        self.chapters.setdefault(
            chapter_num,
            {
                "manuscript words": 0,
                "total words": 0,
            },
        )
        self.chapters[chapter_num]["manuscript words"] += scene.manuscript_info["manuscript_words"]
        self.chapters[chapter_num]["total words"] += scene.manuscript_info["total_words"]
        self.manuscript_words += scene.manuscript_info["manuscript_words"]
        self.total_words += scene.manuscript_info["total_words"]
        pov = scene.manuscript_info.get("pov")
        if pov:
            self.povs.setdefault(
                pov,
                {
                    "scenes": 0,
                    "chapters": [],
                    "populated scenes": 0,
                    "populated chapters": [],
                    "manuscript words": 0,
                    "total words": 0,
                },
            )
            self.povs[pov]["scenes"] += 1
            if chapter_num not in self.povs[pov]["chapters"]:
                self.povs[pov]["chapters"].append(chapter_num)
            self.povs[pov]["manuscript words"] += scene.manuscript_info["manuscript_words"]
            self.povs[pov]["total words"] += scene.manuscript_info["total_words"]
            if scene.manuscript_info["manuscript_words"]:
                self.povs[pov]["populated scenes"] += 1
                if chapter_num not in self.povs[pov]["populated chapters"]:
                    self.povs[pov]["populated chapters"].append(chapter_num)
        characters = scene.manuscript_info.get("characters")
        if characters:
            self.scenes[scene.manuscript_info["title"]]["characters"] = characters
            # Chapter chars; make sure this is unique
            chap = self.chapters[chapter_num]
            chap.setdefault("characters", [])
            chap["characters"].extend(characters)
            chap["characters"] = list(set(chap["characters"]))

    @property
    def scene_average(self):
        """Get the average words per scene."""
        populated_scene_count = 0
        total = {
            "manuscript": 0,
            "total": 0,
        }
        average = {}
        for scene in self.scenes.values():
            if not scene["manuscript words"]:
                continue
            total["manuscript"] += scene["manuscript words"]
            total["total"] += scene["total words"]
            populated_scene_count += 1
        average["populated manuscript words"] = round_to_one_decimal(
            total["manuscript"] / populated_scene_count
        )
        average["populated total words"] = round_to_one_decimal(
            total["total"] / populated_scene_count
        )
        average["num scenes"] = f"{populated_scene_count} / {len(self.scenes)}"
        return average

    @property
    def chapter_average(self):
        """Get the average words per chapter."""
        populated_chapter_count = 0
        total = {
            "manuscript": 0,
            "total": 0,
        }
        average = {}
        for chapter in self.chapters.values():
            if not chapter["manuscript words"]:
                continue
            total["manuscript"] += chapter["manuscript words"]
            total["total"] += chapter["total words"]
            populated_chapter_count += 1
        average["populated manuscript words"] = round_to_one_decimal(
            total["manuscript"] / populated_chapter_count
        )
        average["populated total words"] = round_to_one_decimal(
            total["total"] / populated_chapter_count
        )
        average["num chapters"] = f"{populated_chapter_count} / {len(self.chapters)}"
        return average

    @property
    def povs_with_average(self):
        """Get the povs with the chapter and scene average words."""
        povs = deepcopy(self.povs)
        for _, stats in povs.items():
            stats["num_chapters"] = len(stats["chapters"])
            num_populated_chapters = len(stats["populated chapters"])
            if stats["populated scenes"]:
                stats["scene_average"] = {
                    "manuscript": round_to_one_decimal(
                        stats["manuscript words"] / stats["populated scenes"]
                    ),
                    "total": round_to_one_decimal(stats["total words"] / stats["populated scenes"]),
                }
            if num_populated_chapters:
                stats["chapter_average"] = {
                    "manuscript": round_to_one_decimal(
                        stats["manuscript words"] / num_populated_chapters
                    ),
                    "total": round_to_one_decimal(stats["total words"] / num_populated_chapters),
                }
        return povs

    def stats(self):
        """Get the book stats."""
        return {
            "book": self.book_num,
            "manuscript_words": self.manuscript_words,
            "total_words": self.total_words,
            "scene_average": self.scene_average,
            "chapter average": self.chapter_average,
            "chapters": self.chapters,
            "scenes": self.scenes,
            "povs": self.povs_with_average,
        }


# Functions {{{1
def get_frontmatter_and_body(contents, hack_yaml=False):
    """Get the frontmatter and body of a markdown file."""
    in_comment = False
    frontmatter = ""
    body = ""

    for line in contents.splitlines():
        if line == "---":
            in_comment = not in_comment
            continue
        if in_comment:
            if hack_yaml:
                frontmatter = f"{frontmatter}{unwikilink(line)}\n"
            else:
                frontmatter = f"{frontmatter}{line}\n"
        else:
            body = f"{body}{line}\n"
    return frontmatter, body


def get_markdown_file(path, contents=None, hack_yaml=False):
    """Get the markdown file"""
    if contents is None:
        with open(path, encoding="utf-8") as fh:
            contents = fh.read()
    return MarkdownFile(path, contents, hack_yaml)


def update_stats(path, contents, books, stats, hack_yaml=False):
    """Update the stats with the markdown file at `path`."""
    md_file = MarkdownFile(path, contents, hack_yaml)
    stats["total"]["files"] += 1
    stats["total"]["words"] += md_file.manuscript_info["total_words"]
    if md_file.manuscript_info["is_manuscript"]:
        stats["manuscript"]["files"] += 1
        stats["manuscript"]["words"] += md_file.manuscript_info["manuscript_words"]
    book_num = md_file.manuscript_info.get("book_num")
    if book_num is not None:
        if book_num not in books:
            books[book_num] = Book(book_num)
        books[book_num].add_scene(md_file)
    return md_file.error


def init_books_stats():
    """Get empty books and stats data structures."""

    books = {}
    stats = {
        "manuscript": {
            "words": 0,
            "files": 0,
        },
        "total": {
            "words": 0,
            "files": 0,
        },
    }
    return books, stats


def walk_repo_dir():
    """Walk the current directory to find the books, stats, and errors."""
    books, stats = init_books_stats()
    errors = ""

    repo = Repo(Path("."), search_parent_directories=True)
    path = Path(repo.git.rev_parse("--show-toplevel"))

    for root, dirs, files in os.walk(path):
        if DEBUG:
            print(f"root: {root}")
        for file_ in sorted(files):
            if file_.startswith("_"):
                continue
            if file_.endswith(".md"):
                path = os.path.join(root, file_)
                with open(path, encoding="utf-8") as fh:
                    contents = fh.read()
                error = update_stats(path, contents, books, stats)
                if error:
                    errors += error
        for skip in (".git", ".obsidian"):
            if skip in dirs:
                dirs.remove(skip)
        for dir in dirs:
            if dir.startswith("_"):
                dirs.remove(dir)
    return books, stats, errors


def walk_previous_revision(config, current_stats):
    """Walk the previous day's git revision to determine how much we've changed today."""
    try:
        repo = Repo(Path("."), search_parent_directories=True)
    except InvalidGitRepositoryError:
        return "Not a valid git repo."
    time_fmt = "%Y%m%d"
    today = local_time(time.time(), timezone=config["timezone"]).strftime(time_fmt)
    current_commit = repo.head.commit
    current_commit_date = local_time(
        current_commit.committed_date, timezone=config["timezone"]
    ).strftime(time_fmt)
    if today != current_commit_date and not repo.is_dirty:
        return "No commits today; skipping daily stats."
    books, stats = init_books_stats()
    for rev in repo.iter_commits(repo.head.ref):
        if local_time(rev.committed_date, timezone=config["timezone"]).strftime(time_fmt) != today:
            previous_commit = rev
            break
    else:
        return "Can't find the previous commit!"

    for blob in previous_commit.tree.traverse():
        if blob.name.endswith(".md"):
            contents = blob.data_stream.read().decode("utf-8")
            update_stats(blob.path, contents, books, stats, hack_yaml=True)
    return f"""Previous revision: {previous_commit.hexsha}
Today:
    {current_stats["manuscript"]["files"] - stats["manuscript"]["files"]} manuscript files
    {current_stats["manuscript"]["words"] - stats["manuscript"]["words"]} manuscript words
    {current_stats["total"]["files"] - stats["total"]["files"]} total files
    {current_stats["total"]["words"] - stats["total"]["words"]} total words"""


def write_markdown_file(path, markdown_file):
    """Helper function to update the frontmatter of a markdown file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            f"""---
{yaml_string(markdown_file.parsed_yaml).rstrip()}
---
{markdown_file.body}"""
        )
