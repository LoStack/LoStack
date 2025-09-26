"""
Fetches Bootswatch theme CSS and files
Sep 2025 - Andrew Spangler
"""
 
import requests
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"

THEMES = [
    "brite", "cerulean", "cosmo", "cyborg", "darkly", "flatly",
    "journal", "litera", "lumen", "lux", "materia", "minty",
    "morph", "pulse", "quartz", "sandstone", "simplex", "sketchy",
    "slate", "solar", "spacelab", "superhero", "united", "vapor",
    "yeti", "zephyr"
]

def main():
    for theme in THEMES:
        url = f"https://bootswatch.com/5/{theme}/bootstrap.min.css"
        output = STATIC / "css" / "bootswatch" / theme / "bootstrap.min.css"
        
        output.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            r = requests.get(url)
            r.raise_for_status()
            output.write_text(r.text)
            print(f"GOT {theme}")
        except Exception as e:
            print(f"FAILED {theme}: {e}")

if __name__ == "__main__":
    main()