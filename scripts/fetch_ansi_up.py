"""
Fetches ansi_up.js file
Sep 2025 - Andrew Spangler
"""

import os
import requests
from pathlib import Path

VERSION = "5.1.0"  # ANSI Up version to download
STATIC = Path(__file__).resolve().parent.parent / "static"

def main():

    # Create target directory
    js_extract = STATIC / "js" / "ansi_up" / f"{VERSION}"
    js_extract.mkdir(parents=True, exist_ok=True)

    url = f"https://cdn.jsdelivr.net/npm/ansi_up@{VERSION}/ansi_up.min.js"
    print(f"Downloading {url}")
    r = requests.get(url)
    r.raise_for_status()
    # Save the minified JS file
    output_path = js_extract / "ansi_up.min.js"
    output_path.write_text(r.text, encoding="utf-8")
    print(f"Downloaded {output_path}")

    url = f"https://cdn.jsdelivr.net/npm/ansi_up@{VERSION}/ansi_up.ts"
    print(f"Downloading {url}")
    r = requests.get(url)
    r.raise_for_status()
    # Save the minified JS file
    output_path = js_extract / "ansi_up.ts"
    output_path.write_text(r.text, encoding="utf-8")
    print(f"Downloaded {output_path}")

    print("Done")

if __name__ == "__main__":
    main()