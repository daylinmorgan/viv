#!/usr/bin/env python3
"""
# Viv env is named

Meaning that it will save it within the viv cache not using a hash.

*This environment could then be reused by specifying the name*
"""

__import__("viv").activate("rich", name="rich-env")

from rich.console import Console
from rich.markdown import Markdown

console = Console()
md = Markdown(__doc__)
console.print(md)
