"""
Fetched Homarr dashboard icons 
AI, polished by Andrew Spangler - Sept 2025
"""

import subprocess
import shutil
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static" / "png" / "dashboard-icons"

class GitDownloader:
    def __init__(self, repo: str, branch: str = "main", output_dir: str = "repos"):
        """
        GitHub repo downloader (via git clone).
        :param repo: GitHub repo in "owner/repo" format.
        :param branch: Branch or tag to clone (default: main).
        :param output_dir: Parent folder where repo will be placed.
        """
        self.repo = repo
        self.branch = branch
        self.output_dir = Path(output_dir).resolve()
        self.repo_dir = self.output_dir / repo.split("/")[-1]

    def clone(self) -> Path | None:
        """Shallow clone repo into output_dir. Returns Path if successful, else None."""
        if self.repo_dir.exists():
            print(f"Removing existing {self.repo_dir}")
            shutil.rmtree(self.repo_dir)

        url = f"https://github.com/{self.repo}.git"
        print(f"Cloning {url}@{self.branch} into {self.repo_dir}")

        try:
            subprocess.run(
                ["git", "clone", "--depth=1", "--branch", self.branch, url, str(self.repo_dir)],
                check=True,
            )
            print("Clone complete")
            return self.repo_dir
        except subprocess.CalledProcessError as e:
            print(f"Git clone failed: {e}")
            return None

    def get_path(self) -> Path:
        """Return path to the cloned repo."""
        return self.repo_dir


def main():
    repo = "homarr-labs/dashboard-icons"
    branch = "main"

    downloader = GitDownloader(repo=repo, branch=branch, output_dir="external")
    repo_path = downloader.clone()

    if not repo_path:
        return

    print(f"Repository ready at: {repo_path}")

    # Source and destination
    src = repo_path / "png"
    dst = STATIC

    # Ensure destination exists
    if dst.exists():
        print(f"Removing existing {dst}")
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Copy png/ → STATIC
    print(f"Copying {src} → {dst}")
    shutil.copytree(src, dst)

    # Cleanup repo
    print(f"Removing cloned repo {repo_path}")
    shutil.rmtree(repo_path.parent)

    print("Done!")


if __name__ == "__main__":
    main()
