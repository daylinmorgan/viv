#!/usr/bin/env python3

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).parent.parent / "src/viv/viv.py"


def get_version():
    return subprocess.check_output(
        [
            "git",
            "describe",
            "--tags",
            "--always",
            "--dirty=-dev",
            "--exclude",
            "latest",
        ],
        text=True,
    )


def inc_build(build):
    """increment build number while keeping lexicographic order
    1001 -> 1002
    1999 -> 22000
    22001 -> 22002
    """
    next = str(int(build) + 1)
    return next if build[0] <= next[0] else f"{int(next[0])*11}{next[1:]}"


def release():
    full = get_version()
    if full.endswith("-dev"):
        print("uncommitted changes refusing to proceed")
        sys.exit(1)

    # remove v and git info
    current = full[1:].split("-")[0]
    _, build = current.split(".")
    next = f"{datetime.now().year}.{inc_build(build)}"
    msg = f"bump {current} -> {next}"
    FILE.write_text(
        re.sub(r'__version__ = "[\d\.]+"', f'__version__ = "{next}"', FILE.read_text())
    )
    subprocess.run(["git", "add", FILE])
    subprocess.run(["git", "commit", "-m", msg, "--no-verify"])
    subprocess.run(["git", "tag", f"v{next}"])


if __name__ == "__main__":
    release()
