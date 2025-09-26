"""
AI, polished by Andrew Spangler - Sept 2025

Claude was fed the jsdeliver spec https://data.jsdelivr.com/v1/spec.yaml
and supplied a directory structure of the various Codemirror components.

The desired config system and output file structures were fed in as well as
the data from several of the important endpoints.

Code was re-written from the AI inline script to an object for use in other projects by Andrew Spangler.
TODO: Options to better configure output path and not split css/js
"""

import requests
import aiohttp
import asyncio
import os
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional


class CodeMirrorDownloader:
    """Reusable object for downloading codemirror components dynamically"""

    def __init__(
        self,
        version: str,
        output_dir: os.PathLike,
        config: Optional[Dict[str, Any]] = None,
        use_async: bool = False,
        max_concurrent: int = 10,
    ):
        """
        Downloader for CodeMirror (defaults to v5.65.16).
        config: dict with "modes", "addons", "themes", etc.
        """
        self.version = version
        self.output_dir = Path(output_dir).resolve()

        self.css_dir = self.output_dir / "css" / "codemirror" / version
        self.js_dir = self.output_dir / "js" / "codemirror" / version

        self.base_cdn_url = f"https://cdn.jsdelivr.net/npm/codemirror@{version}/"
        self.api_base = "https://data.jsdelivr.com/v1"
        self.config = config or {}

        self.session = requests.Session()
        self.use_async = use_async
        self.max_concurrent = max_concurrent

        self.core_files = [
            "lib/codemirror.js",
            "lib/codemirror.css",
            "mode/meta.js"
        ]

    def get_version_files(self) -> Dict[str, Any]:
        url = f"{self.api_base}/packages/npm/codemirror@{self.version}"
        params = {"structure": "tree"}
        try:
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"Error fetching version files: {e}")
            return {}

    def extract_files_tree(self, files_data: List[Dict[str, Any]], current_path: str = "") -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        for item in files_data:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            name = item.get("name") or ""
            if item_type == "file":
                file_path = os.path.join(current_path, name).replace("\\", "/").lstrip("/")
                size = int(item.get("size", 0) or 0)
                files.append({"path": file_path, "size": size, "hash": item.get("hash", "")})
            elif item_type == "directory" or (item_type is None and "files" in item):
                dir_path = os.path.join(current_path, name)
                files.extend(self.extract_files_tree(item.get("files", []), dir_path))
        return files

    def filter_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter files based on config (modes, addons, themes)."""
        if not self.config:
            return files

        selected = []
        for category, entries in self.config.items():
            if category == "themes" and entries == "all":
                selected.extend([f for f in files if f["path"].startswith("theme/") and f["path"].endswith(".css")])
            elif isinstance(entries, list):
                for entry in entries:
                    if category == "modes":
                        pattern = f"mode/{entry}/"
                        matched = [f for f in files if f["path"].startswith(pattern)]
                    elif category == "addons":
                        matched = [f for f in files if f["path"].startswith(f"addon/{entry}")]
                    elif category == "themes":
                        matched = [f for f in files if f["path"].startswith(f"theme/{entry}.css")]
                    else:
                        matched = []
                    selected.extend(matched)
        return list({f["path"]: f for f in selected}.values())

    def add_core_files(self, all_files: List[Dict[str, Any]], selected_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        file_map = {f["path"]: f for f in all_files}
        selected_map = {f["path"]: f for f in selected_files}

        for core in self.core_files:
            minified = core.replace(".js", ".min.js").replace(".css", ".min.css")
            if minified in file_map:
                selected_map[minified] = file_map[minified]
            elif core in file_map:
                selected_map[core] = file_map[core]
        return list(selected_map.values())

    def normalize_minified_path(self, path: str) -> str:
        if path.endswith(".js") and not path.endswith(".min.js"):
            return path.replace(".js", ".min.js")
        if path.endswith(".css") and not path.endswith(".min.css"):
            return path.replace(".css", ".min.css")
        return path

    def resolve_output_path(self, file_path: str) -> Optional[Path]:
        if file_path.endswith(".css"):
            return self.css_dir / file_path
        elif file_path.endswith(".js"):
            return self.js_dir / file_path
        return None

    def download_file_sync(self, file_info: Dict[str, Any]) -> bool:
        file_path = file_info["path"]
        preferred_path = self.normalize_minified_path(file_path)
        local_path = self.resolve_output_path(preferred_path)
        if local_path is None:
            return False

        file_url = urljoin(self.base_cdn_url, preferred_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            r = self.session.get(file_url, timeout=30)
            r.raise_for_status()
            local_path.write_bytes(r.content)
            print(f"Saved {'CSS' if local_path.suffix == '.css' else 'JS'}: {preferred_path}")
            return True
        except Exception:
            # fallback
            if preferred_path != file_path:
                try:
                    file_url = urljoin(self.base_cdn_url, file_path)
                    local_path = self.resolve_output_path(file_path)
                    if local_path is None:
                        return False
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    r = self.session.get(file_url, timeout=30)
                    r.raise_for_status()
                    local_path.write_bytes(r.content)
                    print(f"Saved {'CSS' if local_path.suffix == '.css' else 'JS'}: {file_path} (fallback)")
                    return True
                except Exception as e:
                    print(f"Failed {file_path}: {e}")
                    return False
            else:
                print(f"Failed {file_path}")
                return False

    async def download_file_async(self, session: aiohttp.ClientSession, file_info: Dict[str, Any], sem: asyncio.Semaphore) -> bool:
        file_path = file_info["path"]
        preferred_path = self.normalize_minified_path(file_path)
        local_path = self.resolve_output_path(preferred_path)
        if local_path is None:
            return False

        file_url = urljoin(self.base_cdn_url, preferred_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        async with sem:
            try:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        local_path.write_bytes(await resp.read())
                        print(f"Saved {'CSS' if local_path.suffix == '.css' else 'JS'}: {preferred_path}")
                        return True
            except Exception:
                pass  # fallback below

        if preferred_path != file_path:
            file_url = urljoin(self.base_cdn_url, file_path)
            local_path = self.resolve_output_path(file_path)
            if local_path:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                async with sem:
                    try:
                        async with session.get(file_url) as resp:
                            if resp.status == 200:
                                local_path.write_bytes(await resp.read())
                                print(f"Saved {'CSS' if local_path.suffix == '.css' else 'JS'}: {file_path} (fallback)")
                                return True
                    except Exception:
                        pass
        print(f"Failed {file_path}")
        return False

    def download_all(self):
        print(f"Fetching CodeMirror v{self.version}...")
        version_data = self.get_version_files()
        if not version_data:
            print("Failed to fetch version data")
            return

        all_files = self.extract_files_tree(version_data.get("files", []))
        if not all_files:
            print("No files found")
            return

        print(f"Found {len(all_files)} files")

        files = self.filter_files(all_files)
        files = self.add_core_files(all_files=all_files, selected_files=files)

        print(f"Selected {len(files)} files to download")

        if self.use_async:
            asyncio.run(self._download_all_async(files))
        else:
            for f in files:
                self.download_file_sync(f)

    async def _download_all_async(self, files: List[Dict[str, Any]]):
        sem = asyncio.Semaphore(self.max_concurrent)
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_file_async(session, f, sem) for f in files]
            await asyncio.gather(*tasks, return_exceptions=True)



def main():
    static = Path(__file__).resolve().parent.parent / "static"
    config = {
        "modes": [
            "apl",
            "asterisk",
            "clike",
            "clojure",
            "coffeescript",
            "commonlisp",
            "css",
            "d",
            "diff",
            "ecl",
            "erlang",
            "go",
            "groovy",
            "haskell",
            "haxe",
            "htmlembedded",
            "htmlmixed",
            "http",
            "clike",
            "javascript",
            "jinja2",
            "less",
            "lua",
            "markdown",
            "gfm",
            "ntriples",
            "ocaml",
            "pascal",
            "perl",
            "php",
            "pig",
            "properties",
            "python",
            "r",
            "rst",
            "ruby",
            "rust",
            "sass",
            "clike",
            "scheme",
            "shell",
            "sieve",
            "smalltalk",
            "smarty",
            "sql",
            "sparql",
            "stex",
            "tiki",
            "vb",
            "vbscript",
            "velocity",
            "verilog",
            "xml",
            "xquery",
            "yaml",
            "z80"
        ],
        "addons": [
            "edit/closebrackets",
            "edit/openbrackets",
            "lint/lint",
            "mode/overlay",
            "selection/active-line"
        ],
        "themes": "all"
    }
    downloader = CodeMirrorDownloader(
        version="5.65.16",
        output_dir=static,
        config=config,
    )
    downloader.download_all()


if __name__ == "__main__":
    main()
