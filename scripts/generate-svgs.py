#!/usr/bin/env python3

from pathlib import Path
from subprocess import run
from textwrap import dedent
from typing import Tuple

DOCS_PATH = Path(__file__).parent.parent / "docs"
(SAVE_PATH := DOCS_PATH / "svgs").mkdir(exist_ok=True, parents=True)
VIV = Path(__file__).parent.parent / "src" / "viv" / "viv.py"
CLI_DOC_PATH = DOCS_PATH / "cli.md"


(
    cmds := dict.fromkeys(
        (
            "list",
            "manage",
            "freeze",
            "shim",
            "run",
        ),
        [],
    )
).update(
    {
        "manage": ["update", "purge", "show", "install"],
        "env": ["exe", "info", "remove"],
    },
)


cli_doc = """\
---
hide: [navigation]
---

# CLI Reference

![help](./svgs/viv-help.svg)
"""


def yartsu(output: Path, args: Tuple[str, str] | str) -> None:
    if isinstance(args, str):
        args = (args,)
    viv_cmd = " ".join(("viv", *args, "--help"))
    cmd = f"{viv_cmd} | yartsu -w 70 -t '{viv_cmd}' -o {output}"
    run(cmd, shell=True)


if not SAVE_PATH.is_dir():
    SAVE_PATH.mkdir(exist_ok=True, parents=True)

yartsu(SAVE_PATH / "viv-help.svg", "")
for cmd, subcmds in cmds.items():
    p = SAVE_PATH / f"viv-{cmd}-help.svg"
    cli_doc += dedent(
        f"""
    ## {cmd}
    ![cmd](./svgs/{p.name})
    """
    )
    yartsu(p, cmd)
    for subcmd in subcmds:
        p_sub = SAVE_PATH / f"viv-{cmd}-{subcmd}-help.svg"
        cli_doc += dedent(
            f"""
        ### {cmd} {subcmd}
        ![cmd](./svgs/{p_sub.name})
        """
        )
        yartsu(p_sub, [cmd, subcmd])

CLI_DOC_PATH.write_text(cli_doc)
