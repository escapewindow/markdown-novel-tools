#!/usr/bin/env python3
"""Convert an obsidian markdown file to text.

I'm using a custom script because the various Obsidian community pandoc
plugins and the various existing pandoc formats aren't working for me.

"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml
from num2words import num2words

from markdown_novel_tools.config import get_css_path, get_metadata_path
from markdown_novel_tools.constants import ALPHANUM_REGEX, MANUSCRIPT_REGEX
from markdown_novel_tools.utils import find_markdown_files, get_git_revision, local_time


def unwikilink(string):
    """remove the [[ ]] from a string"""
    return re.sub(r"""\[\[([^\]\|]+\|)?([^\]]+)\]\]""", r"\2", string)


def simplify_markdown(contents, ignore_blank_lines=True, plaintext=True):
    """Simplify the markdown - remove frontmatter, unwikilink."""
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
        if ignore_blank_lines and ALPHANUM_REGEX.search(line) is None:
            continue

        line = unwikilink(line)
        if not plaintext:
            # em-dash
            line = re.sub(r"""\([^-]\)\s*--\s*\([^-]\)""", "\1&mdash;\2", line)
        simplified_contents = f"{simplified_contents}{line}\n"
    return simplified_contents


def _header_helper(title, heading_link, style="chapter-only"):
    header = f"""# {title} {{#{heading_link}}}\n\n"""
    toc_link = f"- [{title}](#{heading_link})\n"
    allowed_styles = ("chapter-only", "chapter-and-scene")
    if style not in allowed_styles:
        raise ValueError(f"_header_helper: {style} not in {allowed_styles}!")
    m = MANUSCRIPT_REGEX.match(title)
    if m and style == "chapter-only":
        info = {}
        for attr in ("chapter_num", "scene_num", "POV"):
            info[attr] = m[attr]
        if int(info["scene_num"]) > 1:
            header = "\n\n<br /><br /><center>&ast;&nbsp;&nbsp;&nbsp;&ast;&nbsp;&nbsp;&nbsp;&ast;</center><br /><br />\n\n"
            toc_link = ""
        elif info:
            header_pre = (
                f"""Chapter {num2words(info["chapter_num"]).capitalize()} - {info["POV"]}"""
            )
            header = f"""# {header_pre} {{#{heading_link}}}\n\n"""
            toc_link = f"- [{header_pre}](#{heading_link})\n"
    return header, toc_link


def _doc_header_helper(title):
    m = MANUSCRIPT_REGEX.match(title)
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


def get_header_and_toc(path, format_, heading_num):
    """Get the header and table of contents for the converted file."""
    title = (
        os.path.basename(path).replace(".md", "").replace("_", "-").replace("Book 1 ", "")
    )  # TODO regex
    heading_link = f"heading-{heading_num}"
    header = ""
    if format_ == "pdf":
        header, toc_link = _header_helper(title, heading_link, style="chapter-and-scene")
    elif format_ == "epub":
        header, toc_link = _header_helper(title, heading_link, style="chapter-only")
    elif format_ in ("text"):
        header = f"# {title}\n\n"
        toc_link = ""
    else:
        raise ValueError(f"Unknown format {format_}!")
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


def convert_chapter(args, per_chapter_callback=None):
    """Convert chapters into their own files."""
    ignore_blank_lines = False
    plaintext = False
    separator = "&mdash;"
    artifact_dir = Path(args.artifact_dir)
    chapters = {}
    metadata_path = get_metadata_path(args.config, args.format)
    with open(metadata_path, encoding="utf-8") as fh:
        metadata = fh.read()

    first = True
    for base_path in args.filename:
        for path in find_markdown_files(base_path):
            m = MANUSCRIPT_REGEX.match(os.path.basename(path))
            if not m:
                print(f"skipping {path}")
                continue
            chapter_num = m["chapter_num"]
            if chapters.get(chapter_num) is None:
                first = True
            chapters.setdefault(
                chapter_num,
                f"{metadata}\n\n# Chapter {num2words(chapter_num).capitalize()}{separator}{m["POV"]}\n\n",
            )
            with open(path, encoding="utf-8") as fh:
                simplified_contents = simplify_markdown(
                    fh.read(),
                    ignore_blank_lines=ignore_blank_lines,
                    plaintext=plaintext,
                )
                if not first:
                    chapters[chapter_num] = f"{chapters[chapter_num]}\n\n{'&nbsp;' * 60}#\n\n"
                chapters[chapter_num] = f"{chapters[chapter_num]}{simplified_contents}\n"
            first = False

    if args.clean and os.path.exists(artifact_dir):
        shutil.rmtree(artifact_dir)
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)
    revstr = get_git_revision()
    datestr = local_time(time.time(), timezone=args.config["timezone"]).strftime("%Y.%m.%d")
    subtitle = ""
    if args.subtitle:
        subtitle = f"{args.subtitle}-"

    chapter_markdown = []
    for chapter_num, contents in chapters.items():
        # TODO unhardcode
        chapter_basestr = f"book1-{datestr}-{subtitle}{revstr}-chapter{chapter_num}"
        chapter_md = artifact_dir / f"{chapter_basestr}.md"
        with open(chapter_md, "w", encoding="utf-8") as fh:
            fh.write(contents)
        chapter_markdown.append(chapter_md)
        if per_chapter_callback is not None:
            per_chapter_callback(args, chapter_basestr, chapter_md)


def single_markdown_to_pdf(
    args,
    basename,
    from_,
    artifact_dir=None,
    css_path=None,
):
    """Create a pdf from each chapter"""
    output_pdf = Path(artifact_dir or args.artifact_dir) / f"{basename}.pdf"
    css = css_path or get_css_path(args.config, variant="manuscript_pdf_css_path")
    cmd = [
        "pandoc",
        from_,
        "--pdf-engine=weasyprint",
        "--css",
        css,
        "-o",
        output_pdf,
    ]
    subprocess.check_call(cmd)


def convert_full(args):
    """Convert the full manuscript."""
    contents = ""
    toc = "# Table of Contents\n\n"
    heading_num = 0
    ignore_blank_lines = False
    orig_image = ""
    new_image = ""
    artifact_dir = Path(args.artifact_dir)
    metadata_path = get_metadata_path(args.config, args.format)
    file_sources = args.config["convert"]["frontmatter_files"] + args.filename

    if args.format == "text":
        ignore_blank_lines = True
    if args.format in ("pdf", "epub"):
        metadata, orig_image, new_image = munge_metadata(metadata_path, artifact_dir=artifact_dir)
        contents += metadata
    if args.format in ("markdown", "text"):
        plaintext = True
    else:
        plaintext = False

    for base_path in file_sources:
        for path in find_markdown_files(base_path):
            heading_num += 1
            header, toc_link = get_header_and_toc(path, args.format, heading_num)
            contents += header
            if toc_link:
                toc += toc_link
            with open(path, encoding="utf-8") as fh:
                simplified_contents = simplify_markdown(
                    fh.read(),
                    ignore_blank_lines=ignore_blank_lines,
                    plaintext=plaintext,
                )
                contents += simplified_contents
            contents += "\n"

    if args.format == "epub":
        contents = f"{toc}\n\n{contents}"

    bin_dir = Path("bin")
    if args.clean and os.path.exists(artifact_dir):
        shutil.rmtree(artifact_dir)
    if not os.path.exists(artifact_dir):
        os.mkdir(artifact_dir)
    revstr = get_git_revision()
    datestr = local_time(time.time(), timezone=args.config["timezone"]).strftime("%Y.%m.%d")
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
                get_css_path(args.config, variant="manuscript_pdf_css_path"),
                "-o",
                artifact_dir / f"{output_basestr}.pdf",
            ]
        )

    elif args.format == "epub":
        if args.subtitle:
            subtitle = f"{args.subtitle}\n"
        parsed_metadata = yaml.safe_load(metadata.replace("---", ""))
        cover_title = f"{parsed_metadata['title']}\n{datestr}\n{subtitle}{revstr}"

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
                get_css_path(args.config, variant="epub_css_path"),
                "-o",
                artifact_dir / f"{output_basestr}.epub",
                output_md,
            ]
        )
