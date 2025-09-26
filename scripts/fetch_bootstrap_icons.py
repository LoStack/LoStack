"""
AI, polished by Andrew Spangler - Sept 2025

Rewritten from CodeMirror downloader to download Bootstrap Icons package
Downloads the entire Bootstrap Icons package without filtering.
Highly optimized with asyncio fallback to threading if aiohttp unavailable.

Claude was fed the fetch_codemirror.py file and the url for boostrap icons, and told to remove the filtering.
"""


import os
import requests
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Any
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Try to import async dependencies
try:
    import asyncio
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    print("aiohttp not available, falling back to threaded downloads")


class BootstrapIconsDownloader:
    """Reusable object for downloading Bootstrap Icons package with async/threading fallback"""
    def __init__(
        self,
        version,
        output_dir,
        max_concurrent=100,
        max_workers=20,
    ):
        """
        Downloader for Bootstrap Icons (defaults to latest stable version).
        Downloads the entire package without filtering using async or threading.
        """
        self.version = version
        self.output_dir = Path(output_dir).resolve()
        self.max_concurrent = max_concurrent
        self.max_workers = max_workers
        
        # Create organized directory structure
        self.icons_dir = self.output_dir / "css" / "bootstrap-icons" / f"{version}"
        
        self.base_cdn_url = f"https://cdn.jsdelivr.net/npm/bootstrap-icons@{version}/"
        self.api_base = "https://data.jsdelivr.com/v1"
        
        # For threading fallback
        self.success_count = 0
        self.counter_lock = Lock()

    def get_version_files(self) -> Dict[str, Any]:
        """Fetch the file structure from jsdelivr API (sync)"""
        url = f"{self.api_base}/packages/npm/bootstrap-icons@{self.version}"
        params = {"structure": "tree"}
        
        with requests.Session() as session:
            r = session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()

    def extract_files_tree(self, files_data: List[Dict[str, Any]], current_path: str = "") -> List[str]:
        """Recursively extract all file paths from the jsdelivr tree structure"""
        files = []
        for item in files_data:
            item_type = item.get("type")
            name = item.get("name", "")
            
            if item_type == "file":
                file_path = os.path.join(current_path, name).replace("\\", "/").lstrip("/")
                files.append(file_path)
            elif item_type == "directory" or (item_type is None and "files" in item):
                dir_path = os.path.join(current_path, name)
                files.extend(self.extract_files_tree(item.get("files", []), dir_path))
        
        return files

    if ASYNC_AVAILABLE:
        async def download_file_async(self, session: aiohttp.ClientSession, file_path: str) -> bool:
            """Download a single file asynchronously"""
            local_path = self.icons_dir / file_path
            file_url = urljoin(self.base_cdn_url, file_path)
            
            try:
                # Create directory if needed
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with session.get(file_url) as response:
                    response.raise_for_status()
                    content = await response.read()
                    local_path.write_bytes(content)
                
                # Quick file type for logging
                ext = file_path.split('.')[-1].upper()
                file_type = {
                    'SVG': 'SVG', 'CSS': 'CSS', 'SCSS': 'SCSS', 
                    'JSON': 'JSON', 'WOFF': 'Font', 'WOFF2': 'Font'
                }.get(ext, 'File')
                
                # print(f"✓ {file_type}: {file_path}")
                self.success_count += 1
                return True
                
            except Exception as e:
                print(f"✗ Failed: {file_path} - {e}")
                return False

        async def download_all_async(self, file_paths: List[str]):
            """Download all files asynchronously with connection pooling"""
            # Reset counter for async mode
            self.success_count = 0
            
            # Optimized connector settings
            connector = aiohttp.TCPConnector(
                limit=200,  # Total connection pool size
                limit_per_host=50,  # Per-host limit (jsdelivr)
                ttl_dns_cache=300,  # DNS cache
                use_dns_cache=True,
                enable_cleanup_closed=True
            )
            
            # Optimized timeout settings
            timeout = aiohttp.ClientTimeout(
                total=60,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=30  # Socket read timeout
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'Bootstrap-Icons-Downloader/1.0'}
            ) as session:
                
                # Create semaphore to limit concurrent downloads
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def bounded_download(file_path):
                    async with semaphore:
                        return await self.download_file_async(session, file_path)
                
                # Create all tasks at once
                tasks = [bounded_download(file_path) for file_path in file_paths]
                
                # Execute all downloads concurrently
                await asyncio.gather(*tasks, return_exceptions=True)

    # fallback
    def download_file_threaded(self, file_path: str) -> bool:
        """Download a single file using requests (threaded fallback)"""
        local_path = self.icons_dir / file_path
        file_url = urljoin(self.base_cdn_url, file_path)
        
        # Create directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with requests.Session() as session:
                r = session.get(file_url, timeout=30)
                r.raise_for_status()
                local_path.write_bytes(r.content)
            
            # Simple file type detection for logging
            ext = file_path.split('.')[-1].upper()
            file_type = {
                'SVG': 'SVG', 'CSS': 'CSS', 'SCSS': 'SCSS', 
                'JSON': 'JSON', 'WOFF': 'Font', 'WOFF2': 'Font'
            }.get(ext, 'File')
            
            print(f"✓ {file_type}: {file_path}")
            
            with self.counter_lock:
                self.success_count += 1
            
            return True
            
        except Exception as e:
            print(f"✗ Failed: {file_path} - {e}")
            return False

    def download_all_threaded(self, file_paths: List[str]):
        """Download all files using threading (fallback)"""
        # Reset counter for threaded mode
        self.success_count = 0
        
        # Download files concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(self.download_file_threaded, file_path): file_path 
                for file_path in file_paths
            }
            
            # Process completed downloads
            for future in as_completed(future_to_file):
                future.result()  # This will raise any exceptions that occurred

    def download_all(self):
        """Download all Bootstrap Icons files using best available method"""
        start_time = time.time()
        
        print(f"Fetching Bootstrap Icons v{self.version}...")
        version_data = self.get_version_files()
        
        all_files = self.extract_files_tree(version_data.get("files", []))
        total_files = len(all_files)
        
        if ASYNC_AVAILABLE:
            print(f"Found {total_files} files to download with async ({self.max_concurrent} max concurrent)")
            print("Starting async downloads...\n")
            # Run the async download
            asyncio.run(self.download_all_async(all_files))
        else:
            print(f"Found {total_files} files to download with threading ({self.max_workers} workers)")
            print("Starting threaded downloads...\n")
            # Run threaded download
            self.download_all_threaded(all_files)

        elapsed_time = time.time() - start_time
        print(f"\nDownload complete: {self.success_count}/{total_files} files downloaded successfully")
        print(f"Files saved to: {self.icons_dir}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            print(f"Average speed: {self.success_count/elapsed_time:.1f} files/second")


def main():
    """Main function with default configuration"""
    static = Path(__file__).resolve().parent.parent / "static"
    
    downloader = BootstrapIconsDownloader(
        version="1.13.1",
        output_dir=static,
        max_concurrent=100,
        max_workers=20,
    )
    downloader.download_all()


if __name__ == "__main__":
    main()