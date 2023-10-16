import re
from pathlib import Path

FILES = (
    ("types", [[7, 11]]),
    ("re", [[14, 107]]),
    ("parser", [[20, 691]]),
)

TOMLI_DELIM = ("##### START VENDORED TOMLI #####", "##### END VENDORED TOMLI #####")

TOMLI_PREFACE = """
# MODIFIED FROM https://github.com/hukkin/tomli
# see below for original license
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2021 Taneli Hukkinen
# Licensed to PSF under a Contributor Agreement.
"""

VENDORED_IMPORTS = """
import string  # noqa
from collections.abc import Iterable  # noqa
from functools import lru_cache  # noqa
from datetime import date, datetime, time, timedelta, timezone, tzinfo  # noqa
from types import MappingProxyType  # noqa
from typing import IO, Any, Callable, NamedTuple  # noqa
"""

# REMOVE FOR ACTUAL VENDORED VERSION
tomli_text = VENDORED_IMPORTS
for f, slices in FILES:
    text = Path(f"./tomli/src/tomli/_{f}.py").read_text()
    for indices in slices:
        tomli_text = "\n".join(
            (
                tomli_text,
                # black can add back spaces if it wants
                *[
                    line
                    for line in text.splitlines()[slice(*indices)]
                    if line.strip("\r\n")
                ],
            )
        )

IDENT_PATTERN = r"^(?P<ident>[A-Z_]*) ="
FUNC_PATTERN = r"^def (?P<function>[a-zA-Z_]+)\("

idents = re.findall(IDENT_PATTERN, tomli_text, re.MULTILINE)
funcs = re.findall(FUNC_PATTERN, tomli_text, re.MULTILINE)


# TODO: USE ONE LOOP?
for pat in idents + funcs:
    tomli_text = re.sub(f"(?<!__tomli__){pat}", f"__tomli__{pat}", tomli_text)
# for func in funcs:
# tomli_text = re.sub(f"(?<!__tomli__){func}", f" __tomli__{func}", tomli_text)

# tomli_text += "\n# fmt:on\n"
tomli_text = "\n".join((TOMLI_PREFACE, tomli_text))

viv_src = Path("../src/viv/viv.py")

start, rest = re.split(TOMLI_DELIM[0], viv_src.read_text())
_, rest = re.split(TOMLI_DELIM[1], viv_src.read_text())


viv_src.write_text(
    "\n".join(
        (
            start.strip(),
            "\n",
            TOMLI_DELIM[0],
            tomli_text.strip(),
            TOMLI_DELIM[1],
            "\n",
            rest.strip(),
        )
    )
)
#     re.sub(
#     r"""\n##### START VENDORED TOMLI #####\n*.*\n*##### END VENDORED TOMLI #####\n""",
#         re.escape(tomli_text),
#         viv_src.read_text(),
#         re.MULTILINE,
#     )
# )
