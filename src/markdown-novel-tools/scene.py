#!/usr/bin/env python3
""" Deal with frontmatter of scenes. """

from copy import deepcopy
import datetime
from git import Repo, InvalidGitRepositoryError
import json
import os
from pathlib import Path
import pytz
import re
import shutil
import sys
import time
import yaml

from markdown-novel-tools.constants import ALPHANUM_RE, MANUSCRIPT_RE, TIMEZONE, DEBUG


def round(f):
    """round float f to 1 decimal place"""
    return f"{f:.1f}"


def unwikilink(string, remove=("[[", "]]", "#")):
    """Remove the [[ ]] from a string. Also # for tags."""
    for repl in remove:
        string = string.replace(repl, "")
    return string


class MarkdownFile():
    total_words = 0
    manuscript_words = 0
    book_num = None
    pov = None
    characters = None
    yaml = ""
    error = None

    def __init__(self, path, contents, hack_yaml):
        self.path = Path(path)
        self.is_manuscript = "manuscript" in self.path.parts
        self.title = re.sub(r"""\.md$""", "", os.path.basename(path))
        self.hack_yaml = hack_yaml

        if self.is_manuscript:
            m = MANUSCRIPT_RE.match(self.title)
            if m:
                for attr in ("book_num", "chapter_num", "scene_num"):
                    setattr(self, attr, m[attr])

        if DEBUG:
            print(f"{path}: ", end="")

        self.count_words(contents)

        if DEBUG:
            print(f"{vars(self)}")

    def count_words(self, contents):
        """Count the words in a markdown file, skipping the header and any
           symbol-only lines.

        """
        in_comment = False

        for line in contents.splitlines():
            if line == "---":
                in_comment = not in_comment
                continue
            if in_comment:
                if self.hack_yaml:
                    self.yaml += f"{unwikilink(line)}\n"
                else:
                    self.yaml += f"{line}\n"
            for word in line.split():
                if ALPHANUM_RE.search(word):
                    self.total_words += 1
                    if self.is_manuscript and not in_comment:
                        self.manuscript_words += 1
                elif DEBUG:
                    print(f"skipping {word}")

        if self.book_num and self.yaml:
            try:
                parsed = yaml.safe_load(self.yaml)
            except Exception as e:
                print(str(e))
                self.error = f"### {self.path} yaml is broken.\n{str(e)}\n"
                return
            if parsed.get("POV"):
                self.pov = parsed["POV"]
            for char in sorted(parsed.get("Characters", []) or []):
                if self.characters is None:
                    self.characters = []
                self.characters.append(char)
            if parsed.get("tags", []) in (["scene-reference"], []):
                print(f"{self.path} yaml is missing tags: {parsed.get('tags')}!")


class Book():
    manuscript_words = 0
    total_words = 0
    chapters = {}
    scenes = {}
    povs = {}

    def __init__(self, book_num):
        self.book_num = book_num

    def add_scene(self, scene):
        self.scenes[scene.title] = {
            "manuscript words": scene.manuscript_words,
            "total words": scene.total_words,
        }
        self.chapters.setdefault(scene.chapter_num, {
            "manuscript words": 0,
            "total words": 0,
        })
        self.chapters[scene.chapter_num]["manuscript words"] += scene.manuscript_words
        self.chapters[scene.chapter_num]["total words"] += scene.total_words
        self.manuscript_words += scene.manuscript_words
        self.total_words += scene.total_words
        if scene.pov:
            self.povs.setdefault(scene.pov, {
                "scenes": 0,
                "chapters": [],
                "populated scenes": 0,
                "populated chapters": [],
                "manuscript words": 0,
                "total words": 0,
            })
            self.povs[scene.pov]["scenes"] += 1
            if scene.chapter_num not in self.povs[scene.pov]["chapters"]:
                self.povs[scene.pov]["chapters"].append(scene.chapter_num)
            self.povs[scene.pov]["manuscript words"] += scene.manuscript_words
            self.povs[scene.pov]["total words"] += scene.total_words
            if scene.manuscript_words:
                self.povs[scene.pov]["populated scenes"] += 1
                if scene.chapter_num not in self.povs[scene.pov]["populated chapters"]:
                    self.povs[scene.pov]["populated chapters"].append(scene.chapter_num)
        if scene.characters:
            self.scenes[scene.title]["characters"] = sorted(scene.characters)
            # Chapter chars; make sure this is sorted and unique
            chap = self.chapters[scene.chapter_num]
            chap.setdefault("characters", [])
            chap["characters"].extend(scene.characters)
            chap["characters"] = sorted(list(set(chap["characters"])))

    @property
    def scene_average(self):
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
        average["populated manuscript words"] = round(total["manuscript"] / populated_scene_count)
        average["populated total words"] = round(total["total"] / populated_scene_count)
        average["num scenes"] = f"{populated_scene_count} / {len(self.scenes)}"
        return average

    @property
    def chapter_average(self):
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
        average["populated manuscript words"] = round(total["manuscript"] / populated_chapter_count)
        average["populated total words"] = round(total["total"] / populated_chapter_count)
        average["num chapters"] = f"{populated_chapter_count} / {len(self.chapters)}"
        return average

    @property
    def povs_with_average(self):
        povs = deepcopy(self.povs)
        for pov, stats in povs.items():
            stats["num_chapters"] = len(stats["chapters"])
            num_populated_chapters = len(stats["populated chapters"])
            if stats["populated scenes"]:
                stats["scene_average"] = {
                    "manuscript": round(stats["manuscript words"] / stats["populated scenes"]),
                    "total": round(stats["total words"] / stats["populated scenes"]),
                }
            if num_populated_chapters:
                stats["chapter_average"] = {
                    "manuscript": round(stats["manuscript words"] / num_populated_chapters),
                    "total": round(stats["total words"] / num_populated_chapters),
                }
        return povs

    def stats(self):
        return {
            "book": i,
            "manuscript_words": self.manuscript_words,
            "total_words": self.total_words,
            "scene_average": self.scene_average,
            "chapter average": self.chapter_average,
            "chapters": self.chapters,
            "scenes": self.scenes,
            "povs": self.povs_with_average,
        }


def update_stats(path, contents, books, stats, hack_yaml=False):
    md_file = MarkdownFile(path, contents, hack_yaml)
    stats["total"]["files"] += 1
    stats["total"]["words"] += md_file.total_words
    if md_file.is_manuscript:
        stats["manuscript"]["files"] += 1
        stats["manuscript"]["words"] += md_file.manuscript_words
    if md_file.book_num is not None:
        if md_file.book_num not in books:
            books[md_file.book_num] = Book(md_file.book_num)
        books[md_file.book_num].add_scene(md_file)
    return md_file.error


def init_books_stats():
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


def walk_current_dir():
    books, stats = init_books_stats()
    errors = ""

    path = Path(__file__).parent.parent

    for root, dirs, files in os.walk(path):
        if DEBUG:
            print(f"root: {root}")
        for file_ in sorted(files):
            if file_.endswith(".md"):
                path = os.path.join(root, file_)
                with open(path) as fh:
                    contents = fh.read()
                error = update_stats(path, contents, books, stats)
                if error:
                    errors += error
        for skip in (".git", ".obsidian", "_output"):
            if skip in dirs:
                dirs.remove(skip)
    return books, stats, errors


def local_time(timestamp):
    utc_tz = pytz.utc
    local_tz = pytz.timezone(TIMEZONE)
    utc_dt = datetime.datetime.fromtimestamp(timestamp, utc_tz)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


def walk_previous_revision(current_books, current_stats):
    try:
        repo = Repo(Path(__file__).parent.parent)
    except InvalidGitRepositoryError:
        return "Not a valid git repo."
    time_fmt = "%Y%m%d"
    today = local_time(time.time()).strftime(time_fmt)
    current_commit = repo.head.commit
    current_commit_date = local_time(current_commit.committed_date).strftime(time_fmt)
    if today != current_commit_date and not repo.is_dirty:
        return "No commits today; skipping daily stats."
    books, stats = init_books_stats()
    for rev in repo.iter_commits(repo.head.ref):
        if local_time(rev.committed_date).strftime(time_fmt) != today:
            previous_commit = rev
            break
    else:
        return "Can't find the previous commit!"

    for blob in previous_commit.tree.traverse():
        if blob.name.endswith(".md"):
            contents = blob.data_stream.read().decode("utf-8")
            update_stats(blob.path, contents, books, stats, hack_yaml=True)
    return f"""Today:
    {current_stats["manuscript"]["files"] - stats["manuscript"]["files"]} manuscript files
    {current_stats["manuscript"]["words"] - stats["manuscript"]["words"]} manuscript words
    {current_stats["total"]["files"] - stats["total"]["files"]} total files
    {current_stats["total"]["words"] - stats["total"]["words"]} total words"""


if __name__ == "__main__":
    artifact_dir = Path("_output")
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)

    books, stats, errors = walk_current_dir()
    for i, book in books.items():
        book_stats = book.stats()
        path = artifact_dir / f"book{i}.json"
        with open(path, "w") as fh:
            json.dump(book_stats, fh, indent=4)
        print(json.dumps(book_stats, indent=4))

    summary = f"""Manuscript markdown files: {stats['manuscript']['files']}
Manuscript words: {stats['manuscript']['words']}
Total markdown files: {stats['total']['files']}
Total words: {stats['total']['words']}

{walk_previous_revision(books, stats)}"""
    print(summary)
    with open(artifact_dir / "summary.txt", "w") as fh:
        print(summary, file=fh)

    if errors:
        print(f"Bustage in one or more files!\n{errors}")
        sys.exit(len(errors))
