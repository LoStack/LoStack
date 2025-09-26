"""
Fetches js-yaml.js file
Sep 2025 - Andrew Spangler
"""

import os
import requests
from pathlib import Path

VERSION = "4.1.0"  # JS Yaml version to download
STATIC = Path(__file__).resolve().parent.parent / "static"

def main():

    # Create target directory
    js_extract = STATIC / "js" / f"js-yaml-{VERSION}"
    js_extract.mkdir(parents=True, exist_ok=True)

    js_yaml_url = f"https://cdnjs.cloudflare.com/ajax/libs/js-yaml/{VERSION}/js-yaml.min.js"

    print(f"Downloading {js_yaml_url}")
    r = requests.get(js_yaml_url)
    r.raise_for_status()

    # Save the minified JS file
    output_path = js_extract / "js-yaml.min.js"
    output_path.write_text(r.text, encoding="utf-8")

    print(f"Downloaded {output_path}")
    print("Done")

if __name__ == "__main__":
    main()