#!/usr/bin/env python3
"""Packaging helper for the GestHero extension.

Single source of truth: the loadable extension lives in ``gestHero/`` and is
edited directly. This script does NOT generate the JS/HTML/manifest anymore;
it only:

  1. Copies ``gestHero.svg`` into the extension folder.
  2. Regenerates the PNG icons from that SVG when a converter is available
     (cairosvg / rsvg-convert / macOS sips), leaving the committed icons in
     place otherwise.
  3. Produces a distributable ``gestHero.zip`` of the extension folder.

Run from the repository root:

    python3 build_extension.py
"""
import argparse
import base64
import os
import shutil
import subprocess
import zipfile


# 1x1 transparent PNG used only as a last-resort fallback if no SVG converter
# is available and an icon file is missing.
ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)

ICON_SIZES = (16, 48, 128)


def write_binary(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def render_svg_to_png(svg_path, png_path, size):
    try:
        import cairosvg  # type: ignore

        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            output_width=size,
            output_height=size,
        )
        return True
    except Exception:
        pass

    rsvg_convert = shutil.which("rsvg-convert")
    if rsvg_convert:
        try:
            subprocess.run(
                [
                    rsvg_convert,
                    "-w",
                    str(size),
                    "-h",
                    str(size),
                    "-o",
                    png_path,
                    svg_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    sips = shutil.which("sips")
    if sips:
        try:
            subprocess.run(
                [
                    sips,
                    "-s",
                    "format",
                    "png",
                    "-z",
                    str(size),
                    str(size),
                    svg_path,
                    "--out",
                    png_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    return False


def refresh_icons(root, svg_source):
    """Regenerate PNG icons from the SVG when possible; never clobber a good
    committed icon with the 1x1 fallback."""
    if os.path.isfile(svg_source):
        shutil.copyfile(svg_source, os.path.join(root, "gestHero.svg"))

    fallback_bytes = base64.b64decode(ICON_PNG_BASE64)
    converted_any = False
    for size in ICON_SIZES:
        target = os.path.join(root, f"icon{size}.png")
        if os.path.isfile(svg_source) and render_svg_to_png(svg_source, target, size):
            converted_any = True
        elif not os.path.isfile(target):
            # Only fall back when nothing is there to avoid replacing real icons.
            write_binary(target, fallback_bytes)
    if converted_any:
        print("Regenerated icons from SVG.")
    else:
        print("Kept existing PNG icons (no SVG converter available).")


def build_zip(root, output):
    if os.path.isfile(output):
        os.remove(output)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for current, _dirs, files in os.walk(root):
            for name in files:
                full = os.path.join(current, name)
                arcname = os.path.relpath(full, os.path.dirname(root))
                archive.write(full, arcname)
    print("Created package:", output)


def main():
    parser = argparse.ArgumentParser(description="Package the GestHero extension.")
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Only refresh icons; skip building the distributable zip.",
    )
    args = parser.parse_args()

    repo_root = os.getcwd()
    root = os.path.join(repo_root, "gestHero")
    if not os.path.isdir(root):
        raise SystemExit(f"Extension folder not found: {root}")

    svg_source = os.path.join(repo_root, "gestHero.svg")
    refresh_icons(root, svg_source)

    if not args.no_zip:
        build_zip(root, os.path.join(repo_root, "gestHero.zip"))

    print("Extension ready in:", root)


if __name__ == "__main__":
    main()
