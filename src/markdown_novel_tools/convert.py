#!/usr/bin/env python3
"""Convert an obsidian markdown file to text.

I'm using a custom script because the various Obsidian community pandoc
plugins and the various existing pandoc formats aren't working for me.

"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from pprint import pprint

import pytz
from git import InvalidGitRepositoryError, Repo
from num2words import num2words

from markdown_novel_tools.constants import ALPHANUM_RE, MANUSCRIPT_RE, TIMEZONE
from markdown_novel_tools.utils import find_markdown_files


def unwikilink(string):
    """remove the [[ ]] from a string"""
    return re.sub(r"""\[\[([^\]\|]+\|)?([^\]]+)\]\]""", r"\2", string)


def simplify_markdown(contents, ignore_blank_lines=True):
    in_meta = False
    simplified_contents = ""
    for line in contents.splitlines():
        if line == "---":
            in_meta = not in_meta
            continue

        # Ignore metadata
        if in_meta:
            continue

        # Ignore blank lines
        if ignore_blank_lines and ALPHANUM_RE.search(line) is None:
            continue

        line = unwikilink(line)
        simplified_contents = f"{simplified_contents}{line}\n"
    return simplified_contents


def parse_args(args):
    """Parse commandline args."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=("pdf", "chapter-pdf", "text", "epub", "docx", "odt"),
        default="text",
    )
    parser.add_argument("--subtitle")
    parser.add_argument("--artifact-dir", default="_output")
    parser.add_argument("filename", nargs="+")
    parsed_args = parser.parse_args(args)
    if format in ("pdf", "epub", "docx", "odt", "chapter-pdf"):
        if not shutil.which("pandoc"):
            print(f"`{format}` format requires `pandoc`! Exiting...", file=sys.stderr)
            sys.exit(1)
    if format == "epub":
        if not shutil.which("magick"):
            print(f"`{format}` format requires `imagemagick`! Exiting...", file=sys.stderr)
            sys.exit(1)
    return parsed_args


def _header_helper(title, heading_link, style="chapter-only"):
    header = f"""# {title} {{#{heading_link}}}\n\n"""
    toc_link = f"- [{title}](#{heading_link})\n"
    allowed_styles = ("chapter-only", "chapter-and-scene")
    if style not in allowed_styles:
        raise (f"_header_helper: {style} not in {allowed_styles}!")
    m = MANUSCRIPT_RE.match(title)
    if m and style == "chapter-only":
        info = {}
        for attr in ("chapter_num", "scene_num", "POV"):
            info[attr] = m[attr]
        if int(info["scene_num"]) > 1:
            header = "\n\n<br /><br /><center>&ast;&nbsp;&nbsp;&nbsp;&ast;&nbsp;&nbsp;&nbsp;&ast;</center><br /><br />\n\n"
            toc_link = ""
        elif info:
            header_pre = f"""Chapter {int(info["chapter_num"])} - {info["POV"]}"""
            header = f"""# {header_pre} {{#{heading_link}}}\n\n"""
            toc_link = f"- [{header_pre}](#{heading_link})\n"
    return header, toc_link


def _doc_header_helper(title):
    m = MANUSCRIPT_RE.match(title)
    if m:
        info = {}
        for attr in ("chapter_num", "scene_num", "POV"):
            info[attr] = m[attr]
        if int(info["scene_num"]) > 1:
            # header = "\n\n<br /><br /><center>#</center><br /><br />\n\n"
            header = "\n\n<br /><br /><center>&ast;&nbsp;&nbsp;&nbsp;&ast;&nbsp;&nbsp;&nbsp;&ast;</center><br /><br />\n\n"
        elif info:
            header = f"""# Chapter {num2words(info["chapter_num"]).capitalize()} - {info["POV"]}"""
            if int(info["chapter_num"]) > 1:
                header = f"\n\\newpage\n\n{header}"
    return header


def get_header_and_toc(path, format, heading_num):
    title = (
        os.path.basename(path).replace(".md", "").replace("_", "-").replace("Book 1 ", "")
    )  # TODO regex
    heading_link = f"heading-{heading_num}"
    header = ""
    if format == "pdf":
        header, toc_link = _header_helper(title, heading_link, style="chapter-and-scene")
    elif format == "epub":
        header, toc_link = _header_helper(title, heading_link, style="chapter-only")
    elif format in ("docx", "odt"):
        header = _doc_header_helper(title)
        toc_link = ""
    elif format in ("text"):
        header = f"# {title}\n\n"
        toc_link = ""
    else:
        raise Exception(f"Unknown format {format}!")
    return header, toc_link


def munge_metadata(path, artifact_dir):
    """Read the metadata file, get the original image path, replace it with a new image path

    Returns: tuple(munged metadata contents, orig_image path, new_image path)
    """
    contents = ""
    if not os.path.exists(path):
        print(f"{path} doesn't exist!")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("cover-image:"):
                orig_image = line.replace("cover-image:", "").strip()
                new_image = artifact_dir / os.path.basename(orig_image)
                line = f"cover-image: {new_image}\n"
            contents += line
    return (contents, orig_image, new_image)


def get_git_revision():
    repo = Repo(Path(os.getcwd()))
    rev = str(repo.head.commit)[0:12]
    if repo.is_dirty():
        rev = f"{rev}+"
    return rev


def local_time(timestamp):
    utc_tz = pytz.utc
    local_tz = pytz.timezone(TIMEZONE)
    utc_dt = datetime.datetime.fromtimestamp(timestamp, utc_tz)
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


def convert_chapter(args):
    contents = ""
    ignore_blank_lines = False
    artifact_dir = Path(args.artifact_dir)
    chapters = {}
    metadata_path = Path("skeleton/Book 1 Metadata.txt")  # TODO unhardcode
    with open(metadata_path, encoding="utf-8") as fh:
        metadata = fh.read()

    for base_path in args.filename:
        for path in find_markdown_files(base_path):
            m = MANUSCRIPT_RE.match(os.path.basename(path))
            if not m:
                print(f"skipping {path}")
                continue
            chapter_num = m["chapter_num"]
            chapters.setdefault(
                chapter_num, f"{metadata}\n\n# Chapter {chapter_num} - {m['POV']}\n\n"
            )
            with open(path, encoding="utf-8") as fh:
                simplified_contents = simplify_markdown(
                    fh.read(), ignore_blank_lines=ignore_blank_lines
                )
                chapters[chapter_num] = f"{chapters[chapter_num]}{simplified_contents}\n"

    bin_dir = Path("bin")
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)
    revstr = get_git_revision()
    datestr = local_time(time.time()).strftime("%Y.%m.%d")
    subtitle = ""
    if args.subtitle:
        subtitle = f"{args.subtitle}-"

    for chapter_num in chapters.keys():
        chapter_basestr = f"book1-{datestr}-{subtitle}{revstr}-chapter{chapter_num}"
        chapter_md = artifact_dir / f"{chapter_basestr}.md"
        chapter_pdf = artifact_dir / f"{chapter_basestr}.pdf"
        with open(chapter_md, "w", encoding="utf-8") as fh:
            fh.write(chapters[chapter_num])
        cmd = [
            "pandoc",
            chapter_md,
            "--pdf-engine=weasyprint",
            "--css",
            bin_dir / "pdf.css",
            "-o",
            chapter_pdf,
        ]
        subprocess.check_call(cmd)


def convert_full(args):
    contents = ""
    toc = "# Table of Contents\n\n"
    heading_num = 0
    ignore_blank_lines = False
    orig_image = ""
    new_image = ""
    artifact_dir = Path(args.artifact_dir)
    metadata_path = Path("skeleton/Book 1 Metadata.txt")  # TODO unhardcode
    if args.format in ("docx", "odt"):
        file_sources = args.filename
    else:
        file_sources = [
            "skeleton/Book 1 Copyright.md",
            "skeleton/Book 1 Dedication.md",
            "skeleton/Book 1 Author's Note.md",
            "skeleton/Book 1 Pronunciation Guide.md",
        ] + args.filename  # TODO unhardcode

    if args.format == "text":
        ignore_blank_lines = True
    if args.format in ("pdf", "epub"):
        metadata, orig_image, new_image = munge_metadata(metadata_path, artifact_dir=artifact_dir)
        contents += metadata

    for base_path in file_sources:
        for path in find_markdown_files(base_path):
            heading_num += 1
            header, toc_link = get_header_and_toc(path, args.format, heading_num)
            contents += header
            if toc_link:
                toc += toc_link
            with open(path, encoding="utf-8") as fh:
                simplified_contents = simplify_markdown(
                    fh.read(), ignore_blank_lines=ignore_blank_lines
                )
                contents += simplified_contents
            contents += "\n"

    if args.format == "epub":
        contents = f"{toc}\n\n{contents}"

    bin_dir = Path("bin")
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)
    revstr = get_git_revision()
    datestr = local_time(time.time()).strftime("%Y.%m.%d")
    subtitle = ""
    if args.subtitle:
        subtitle = f"{args.subtitle}-"
    output_basestr = f"book1-{datestr}-{subtitle}{revstr}"
    output_md = artifact_dir / f"{output_basestr}.md"
    with open(output_md, "w", encoding="utf-8") as fh:
        fh.write(contents)

    if args.format == "pdf":
        subprocess.check_call(
            [
                "pandoc",
                output_md,
                "--pdf-engine=weasyprint",
                "--toc",
                "--css",
                bin_dir / "pdf.css",
                "-o",
                artifact_dir / f"{output_basestr}.pdf",
            ]
        )

    elif args.format == "epub":
        if args.subtitle:
            subtitle = f"{args.subtitle}\n"
        cover_title = f"The Seer of Redgate\n{datestr}\n{subtitle}{revstr}"

        # Create cover image
        subprocess.check_call(
            [
                "magick",
                orig_image,
                "-pointsize",
                "24",
                "-fill",
                "white",
                "-annotate",
                "+50+50",
                cover_title,
                new_image,
            ]
        )

        # Create epub
        subprocess.check_call(
            [
                "pandoc",
                "-f",
                "markdown",
                "-t",
                "epub",
                "--css",
                "bin/epub.css",
                "-o",
                artifact_dir / f"{output_basestr}.epub",
                output_md,
            ]
        )

    elif args.format in ("docx", "odt"):
        data_dir = bin_dir / "data" / "pandoc"
        env = os.environ
        if args.format == "odt":
            template = data_dir / "default.opendocument"
            env["PANDOC_NEWPAGE_ODT_STYLE"] = "1"
        else:
            template = data_dir / "default.openxml"
        subprocess.check_call(
            [
                "pandoc",
                "-f",
                "markdown",
                "-t",
                args.format,
                "--data-dir",
                data_dir,
                "--template",
                template,
                "--metadata-file",
                metadata_path,
                "--lua-filter",
                data_dir / "pagebreak.lua",
                "-o",
                artifact_dir / f"{output_basestr}.{args.format}",
                output_md,
            ],
            env=env,
        )


def convert():
    args = parse_args(sys.argv[1:])
    if args.format in ("chapter-pdf",):
        convert_chapter(args)
    else:
        convert_full(args)
