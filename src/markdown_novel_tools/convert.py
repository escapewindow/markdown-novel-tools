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
from markdown_novel_tools.constants import (
    ALPHANUM_REGEX,
    MANUSCRIPT_REGEX,
    SCENE_SPLIT_ASTERISK,
    SCENE_SPLIT_PLAINTEXT,
    SCENE_SPLIT_POUND,
    SCENE_SPLIT_REGEX,
)
from markdown_novel_tools.utils import find_markdown_files, get_git_revision, local_time, mkdir


def unwikilink(string):
    """remove the [[ ]] from a string"""
    return re.sub(r"""\[\[([^\]\|]+\|)?([^\]]+)\]\]""", r"\2", string)


def simplify_markdown(
    contents, ignore_blank_lines=True, plaintext=True, scene_split_string=None, **kwargs
):
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
            line = re.sub(r"""([^-])(\s+-\s+|--)([^-]|$)""", r"\1&mdash;\3", line)
            # nbsp between single quote and double quote
            line = re.sub(r"'\"", r"'&nbsp;&#8221;", line)
            line = re.sub(r"\"'", r"&#8220;&nbsp;'", line)
            if scene_split_string:
                line = re.sub(SCENE_SPLIT_REGEX, scene_split_string, line)
        simplified_contents = f"{simplified_contents}{line}\n"
    return simplified_contents


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


def get_output_basestr(
    args, format_string="book{book_num}-{datestr}-{subtitle}{revstr}", repl_dict=None
):
    """Get the basestr for the name of our output file."""
    if repl_dict is None:
        repl_dict = {"book_num": args.config["book_num"]}
        if "{revstr}" in format_string:
            repl_dict["revstr"] = get_git_revision()
        if "{datestr}" in format_string:
            repl_dict["datestr"] = local_time(
                time.time(), timezone=args.config["timezone"]
            ).strftime("%Y.%m.%d")
        if "{subtitle}" in format_string:
            repl_dict["subtitle"] = f"{args.subtitle}-" or ""
    return format_string.format(**repl_dict)


def single_markdown_to_pdf(
    args,
    basename,
    from_,
    toc=False,
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
    if toc:
        cmd.append("--toc")

    subprocess.check_call(cmd)


def convert_simple_pdf(args):
    """Create a non-outline, non-manuscript pdf from a markdown file."""
    mkdir(args.artifact_dir, clean=args.clean)
    for from_ in args.filename:
        output_basestr = re.sub(r"\.md", "", os.path.basename(from_))

        single_markdown_to_pdf(
            args,
            output_basestr,
            from_,
            toc=False,
            artifact_dir=args.artifact_dir,
            css_path=get_css_path(args.config, variant="misc_pdf_css_path"),
        )


def get_format_convert_config(format_):
    """Specify each format's convert config. Might be easier to read if it's explicit?"""
    convert_config = {
        "ignore_blank_lines": False,
        "plaintext": False,
        "title_separator": r"&mdash;",
        "scene_split_string": SCENE_SPLIT_POUND,
        "build_toc": False,
    }
    if format_ == "text":
        convert_config["ignore_blank_lines"] = True
    if format_ in ("markdown", "text"):
        convert_config["plaintext"] = True
        convert_config["scene_split_string"] = SCENE_SPLIT_PLAINTEXT
    if format_ in ("epub", "pdf"):
        convert_config["scene_split_string"] = SCENE_SPLIT_ASTERISK
    if format_ == "epub":
        convert_config["build_toc"] = True
    return convert_config


def _get_title_and_toc(title, heading_link, toc):
    """Helper function to build a atable of contents and links"""
    toc = f"{toc}- [{chapter_title}](#{heading_link})\n"
    title = f"""{title} {{#{heading_link}}}"""
    return title, toc


def _get_converted_chapter_markdown_and_toc(
    paths,
    build_toc=False,
    ignore_blank_lines=False,
    metadata="",
    plaintext=False,
    scene_split_string=SCENE_SPLIT_POUND,
    title_separator=r"&mdash;",
):
    """Helper function to convert all novel markdown files in a path"""
    chapters = {}
    toc = ""
    if build_toc:
        toc = "# Table of Contents\n\n"
    first = True

    for base_path in paths:
        for path in find_markdown_files(base_path):
            m = MANUSCRIPT_REGEX.match(os.path.basename(path))
            if not m:
                print(f"skipping {path}")
                continue
            chapter_num = m["chapter_num"]
            if chapters.get(chapter_num) is None:
                first = True
            chapter_title = (
                f"Chapter {num2words(chapter_num).capitalize()}{title_separator}{m["POV"]}",
            )
            if build_toc:
                chapter_title, toc = _get_title_and_toc(
                    chapter_title, f"heading-{chapter_num}", toc
                )

            chapter_title = f"# {chapter_title}\n\n"
            if metadata:
                chapter_title = f"{metadata}\n\n{chapter_title}"
            chapters.setdefault(chapter_num, chapter_title)
            with open(path, encoding="utf-8") as fh:
                simplified_contents = simplify_markdown(
                    fh.read(),
                    ignore_blank_lines=ignore_blank_lines,
                    plaintext=plaintext,
                    scene_split_string=scene_split_string,
                )
                if not first:
                    chapters[chapter_num] = f"{chapters[chapter_num]}\n\n{scene_split_string}\n\n"
                chapters[chapter_num] = f"{chapters[chapter_num]}{simplified_contents}\n"
            first = False
    return chapters, toc


def convert_chapter(
    args, per_chapter_callback=None, output_basestr=None, plaintext=False, ignore_blank_lines=False
):
    """Convert chapters into their own files."""
    separator = "&mdash;"
    artifact_dir = Path(args.artifact_dir)
    metadata_path = get_metadata_path(args.config, args.format)
    with open(metadata_path, encoding="utf-8") as fh:
        metadata = fh.read()

    mkdir(artifact_dir, clean=args.clean)

    convert_config = get_format_convert_config(args.format)
    chapters, _ = _get_converted_chapter_markdown_and_toc(
        args.filename, metadata=metadata, **convert_config
    )

    chapter_markdown = []
    chapter_count = 0
    for chapter_num, contents in chapters.items():
        chapter_count += 1
        output_basestr = output_basestr or get_output_basestr(args)
        chapter_md = artifact_dir / f"{output_basestr}-chapter{chapter_num}.md"
        if chapter_count == len(chapters):
            contents = f"""{contents}\n\n<span style="font-variant:small-caps;">[END]</span>"""
        chapter_markdown.append(chapter_md)
        if per_chapter_callback is not None:
            per_chapter_callback(args, output_basestr, chapter_md)


def get_front_back_matter(matter_config, convert_config, toc):
    contents = ""
    toc = ""
    for title, path in matter_config.items():
        with open(path, encoding="utf-8") as fh:
            simplified_contents = simplify_markdown(
                fh.read(),
                **convert_config,
            )
        if convert_config["build_toc"]:
            heading_link = title.replace(" ", "-").lower()
            heading_link = f"heading-{heading_link}"
            title, toc = _get_title_and_toc(title, heading_link, toc)
        contents = f"{contents}# {title}\n\n{simplified_contents}\n\n"
    return contents, toc


def convert_full(args):
    """Convert the full manuscript."""
    contents = ""
    heading_num = 0
    orig_image = ""
    new_image = ""
    artifact_dir = Path(args.artifact_dir)
    metadata_path = get_metadata_path(args.config, args.format)
    if args.format in ("pdf", "epub"):
        metadata, orig_image, new_image = munge_metadata(metadata_path, artifact_dir=artifact_dir)
        contents += metadata

    convert_config = get_format_convert_config(args.format)
    chapters, toc = _get_converted_chapter_markdown_and_toc(
        args.filename, metadata=metadata, **convert_config
    )

    front_contents, toc = get_front_back_matter(
        args.config["convert"]["frontmatter_files"], convert_config, toc
    )
    contents = f"{contents}{front_contents}"
    for chapter_contents in chapters.values():
        contents = f"{contents}{chapter_contents}\n"
    back_contents, toc = get_front_back_matter(
        args.config["convert"]["backmatter_files"], convert_config, toc
    )
    contents = f"{contents}{back_contents}"

    if convert_config["build_toc"]:
        contents = f"{toc}\n\n{contents}"

    bin_dir = Path("bin")
    mkdir(artifact_dir, clean=args.clean)
    subtitle = args.subtitle or ""
    revstr = get_git_revision()
    datestr = local_time(time.time(), timezone=args.config["timezone"]).strftime("%Y.%m.%d")
    output_basestr = get_output_basestr(
        args,
        repl_dict={
            "datestr": datestr,
            "revstr": revstr,
            "subtitle": subtitle,
            "book_num": args.config["book_num"],
        },
    )
    output_md = artifact_dir / f"{output_basestr}.md"
    with open(output_md, "w", encoding="utf-8") as fh:
        fh.write(contents)

    if args.format == "pdf":
        single_markdown_to_pdf(
            args,
            output_basestr,
            output_md,
            toc=True,
            artifact_dir=artifact_dir,
            css_path=get_css_path(args.config, variant="manuscript_pdf_css_path"),
        )

    elif args.format == "epub":
        parsed_metadata = yaml.safe_load(metadata.replace("---", ""))
        cover_title = f"{parsed_metadata['title']}\n{datestr}\n{subtitle}\n{revstr}"

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
