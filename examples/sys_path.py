#!/usr/bin/env python3
"""
Embed the viv.py on the sys.path at runtime rather than using PYTHONPATH
"""
import sys

old_sys_path = sys.path.copy()  # noqa


__import__("sys").path.append(
    __import__("os").path.expanduser("~/.local/share/viv")
)  # noqa # isort: off
__import__("viv").use("rich")  # noqa # isort: off

from difflib import unified_diff

from rich import print
from rich.syntax import Syntax

print("[bold italic yellow] Modified Sys.path")
print(
    Syntax(
        "\n".join(
            unified_diff(
                old_sys_path, sys.path, "pre-viv sys.path", "post-viv sys.path"
            )
        ),
        "diff",
        theme="default",
    )
)
