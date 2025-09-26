"""
Fetches and extracts Bootstrap CSS and JS files
Sep 2025 - Andrew Spangler
"""

import json
import os
import re
import requests
import zipfile
import shutil
from pathlib import Path
from io import BytesIO

VERSION = "5.1.3"  # Bootstrap version to download
STATIC = Path(__file__).resolve().parent.parent / "static"

def main():
    # Create target directories
    css_extract = STATIC / "css" / f"bootstrap-{VERSION}"
    js_extract = STATIC / "js" / f"bootstrap-{VERSION}"

    bootstrap_url = f"https://github.com/twbs/bootstrap/releases/download/v{VERSION}/bootstrap-{VERSION}-dist.zip"

    print(f"Downloading {bootstrap_url}")
    r = requests.get(bootstrap_url, stream=True)
    r.raise_for_status()

    # Stream the zip content directly into a BytesIO buffer
    zip_buffer = BytesIO()
    for chunk in r.iter_content(1024):
        zip_buffer.write(chunk)

    # Reset buffer position to beginning for reading
    zip_buffer.seek(0)

    # Extract the entire css and js folders with all their contents
    with zipfile.ZipFile(zip_buffer, "r") as z:
        for member in z.namelist():
            # Check if this is a file in the css or js directories
            if member.startswith(f"bootstrap-{VERSION}-dist/css/") and not member.endswith('/'):
                # Extract to css folder
                relative_path = member.replace(f"bootstrap-{VERSION}-dist/css/", "")
                output_path = css_extract / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with z.open(member) as source:
                    content = source.read()
                    output_path.write_bytes(content)
                print(f"Saved CSS: {relative_path}")
                
            elif member.startswith(f"bootstrap-{VERSION}-dist/js/") and not member.endswith('/'):
                # Extract to js folder  
                relative_path = member.replace(f"bootstrap-{VERSION}-dist/js/", "")
                output_path = js_extract / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with z.open(member) as source:
                    content = source.read()
                    output_path.write_bytes(content)
                print(f"Saved JS: {relative_path}")

    print("Done")
    print(f"CSS files saved to: {css_extract}")
    print(f"JS files saved to: {js_extract}")

if __name__ == "__main__":
    main()