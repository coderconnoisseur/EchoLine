import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_every_package_source_file_is_tracked():
    # A stray .gitignore rule once kept echoline/ui/overlay.py out of git, so
    # fresh clones could not start the app while this machine's tests passed.
    tracked = set(subprocess.run(["git", "ls-files", "echoline"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split())
    on_disk = {path.relative_to(ROOT).as_posix() for path in (ROOT / "echoline").rglob("*")
               if path.suffix in (".py", ".qml") and "__pycache__" not in path.parts}

    assert on_disk - tracked == set()
