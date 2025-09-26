"""
Fetches and cleans Pictogrammers' Material Design Icons
Based roughly on the JS here: https://github.com/Pictogrammers/Browser-Icon-Picker/blob/master/tools/pull-icons.js
Sep 2025 - Andrew Spangler 
Handles zip and icons in-memory then writes them out
"""

import json
import os
import re
import requests
import zipfile
import shutil
from pathlib import Path
from io import BytesIO

VERSION = "7.1.96" # Select version to download 
REPO = "MaterialDesign"
PACKAGE = "@mdi/svg"
STATIC = Path(__file__).resolve().parent.parent / "static"
(STATIC / "svg" / "material-design-icons").mkdir(parents=True, exist_ok=True)

def main():
    svg_final_extract = STATIC / "svg"
    svg_final_extract.mkdir(exist_ok=True)

    svg_url = f"https://github.com/Templarian/{REPO}-SVG/archive/v{VERSION}.zip"

    print(f"Downloading {svg_url}")
    r = requests.get(svg_url, stream=True)
    r.raise_for_status()

    # Stream the zip content directly into a BytesIO buffer
    zip_buffer = BytesIO()
    for chunk in r.iter_content(1024):
        zip_buffer.write(chunk)

    # Reset buffer position to beginning for reading
    zip_buffer.seek(0)

    # Read zip file directly from memory buffer
    pat = re.compile(rf"^MaterialDesign-SVG-{re.escape(VERSION)}/svg/.+\.svg$")
    svg_data = {}

    with zipfile.ZipFile(zip_buffer, "r") as z:
        for member in z.namelist():
            if pat.match(member):
                filename = os.path.basename(member)
                if not filename:
                    continue
                # Read SVG content directly into memory
                with z.open(member) as source:
                    svg_content = source.read().decode('utf-8')
                    svg_data[filename] = svg_content

    print(f"Loaded {len(svg_data)} SVGs into memory")

    r = requests.get(f"https://cdn.jsdelivr.net/npm/{PACKAGE}@{VERSION}/meta.json")
    r.raise_for_status()
    print("Downloaded meta")

    for icon in r.json():
        svg_filename = f"{icon['name']}.svg"
        if svg_filename not in svg_data:
            continue
        svg = svg_data[svg_filename] 
        svg = svg.replace(
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
            "",
        )
        svg = svg.replace(
            ' xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"',
            "",
        )
        svg = svg.replace(f' id="mdi-{icon["name"]}"', "")
        # Save clean SVG
        (STATIC / "svg" / "material-design-icons" / f"{icon['name']}.svg").write_text(svg, encoding="utf-8")

    print("Done")

if __name__ == "__main__":
    main()