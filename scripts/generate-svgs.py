#!/usr/bin/env python3

from pathlib import Path
from subprocess import run
from textwrap import dedent
from typing import Tuple

DOCS_PATH = Path(__file__).parent.parent / "docs"
(SAVE_PATH := DOCS_PATH / "svgs").mkdir(exist_ok=True)
VIV = Path(__file__).parent.parent / "src" / "viv" / "viv.py"
CLI_DOC_PATH = DOCS_PATH / "cli.md"


cmds = {
    "list": [],
    "exe": ["python", "pip"],
    "remove": [],
    "manage": ["update", "purge", "show", "install"],
    "freeze": [],
    "shim": [],
    "run": [],
}


cli_doc = """
# cli

![help](/svgs/viv-help.svg)
"""


def yartsu(output: Path, args: Tuple[str, str] | str) -> None:
    if isinstance(args, str):
        args = (args,)
    cmd = [
        VIV,
        "run",
        "-k",
        "yartsu",
        "--",
        "-w",
        "70",
        "-o",
        output,
        "--",
        "viv",
        *args,
        "--help",
    ]
    run(cmd)


yartsu(SAVE_PATH / "viv-help.svg", "")
for cmd, subcmds in cmds.items():
    p = SAVE_PATH / f"viv-{cmd}-help.svg"
    cli_doc += dedent(
        f"""
    ## {cmd}
    ![cmd](/svgs/{p.name})
    """
    )
    yartsu(p, cmd)
    for subcmd in subcmds:
        p_sub = SAVE_PATH / f"viv-{cmd}-{subcmd}-help.svg"
        cli_doc += dedent(
            f"""
        ### {cmd} {subcmd}
        ![cmd](/svgs/{p_sub.name})
        """
        )
        yartsu(p_sub, [cmd, subcmd])

CLI_DOC_PATH.write_text(cli_doc)
