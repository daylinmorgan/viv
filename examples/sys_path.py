#!/usr/bin/env python3
"""
Embed the viv.py on the sys.path at runtime rather than using PYTHONPATH
"""


__import__("sys").path.append(
    __import__("os").path.expanduser("~/.viv/src")
)  # noqa # isort: off
__import__("viv").activate("pyfiglet")  # noqa # isort: off

import sys

from pyfiglet import Figlet

f = Figlet(font="slant")
print(f.renderText("Viv isn't venv!"))

print("Sys path:")
print("\n".join(sys.path))
