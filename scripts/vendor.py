#!/usr/bin/env python3
import ast
import re
import subprocess
import textwrap
from pathlib import Path
from typing import List

import astor


def remove_docs_and_comments(code):
    parsed = ast.parse(code)
    for node in ast.walk(parsed):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            # set value to empty string which should be ignored by astor.to_source
            node.value = ast.Constant(value="")
        elif (
            (isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef))
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            # add pass to empty functions and class definition
            node.body = [ast.Pass()]
    formatted_code = astor.to_source(parsed)
    pattern = r'^.*"""""".*$'  # remove empty """"""
    formatted_code = re.sub(pattern, "", formatted_code, flags=re.MULTILINE)
    return formatted_code


class Package:
    def __init__(
        self,
        name: str,
        url: str,
        files: List[tuple[str, List[List[int]]]],
        rev: str,
        basepath: Path,
        imports: str = "",
        prefix: str = "",
        suffix: str = "",
        indent: bool = False,
    ):
        self.name = name
        self.files = files
        self.url = url
        self.rev = rev
        self.basepath = basepath
        self.imports = imports
        self.prefix = prefix
        self.suffix = suffix
        self.indent = indent

        self.ensure()
        self.generate_vendored_source()
        self.replace_identifiers()

    def ensure(self):
        dir = Path(__file__).parent / self.name
        if not dir.is_dir():
            subprocess.run(["git", "clone", self.url, dir])
            subprocess.run(["git", "-C", dir, "checkout", self.rev])

    @property
    def start_delim(self) -> str:
        return f"#### START VENDORED {self.name.upper()} ####"

    @property
    def end_delim(self) -> str:
        return f"#### END VENDORED {self.name.upper()} ####"

    def generate_vendored_source(self):
        self.src_text = ""
        for f, slices in self.files:
            og_text = (self.basepath / f"{f}.py").read_text()
            for indices in slices:
                self.src_text = "\n".join(
                    (
                        self.src_text,
                        *[
                            line
                            for line in og_text.splitlines()[slice(*indices)]
                            if line.strip("\r\n")
                        ],
                    )
                )

    def replace_identifiers(self):
        patterns = set.union(
            *[
                set(re.findall(regex, self.src_text, re.MULTILINE))
                for regex in (
                    r"^class (?P<class>[a-zA-Z_]*)(?:\(.*\))?:",
                    r"^(?P<ident>[a-zA-Z_]*) =",
                    r"^def (?P<function>[a-zA-Z_]+)\(",
                )
            ]
        ) - {
            "Key",
        }  # prevent KeyError false positive by leaving Key alone

        for pat in patterns:
            self.src_text = re.sub(
                r'(?P<lead>[\s("\[={])' + pat,
                f"\g<lead>v_{self.name}_{pat}",
                self.src_text,
            )

    def insert(self, base_text: str) -> str:
        start, rest = re.split(self.start_delim, base_text)
        _, rest = re.split(self.end_delim, base_text)
        src = textwrap.indent(
            remove_docs_and_comments(self.src_text.strip()),
            prefix=" " * (4 if self.indent else 0),
        )
        return "\n".join(
            (
                start.strip(),
                "\n",
                self.start_delim,
                self.prefix + self.imports + src + self.suffix,
                self.end_delim,
                "\n",
                rest.strip(),
            )
        )


PACKAGES = [
    Package(
        name="packaging",
        url="https://github.com/pypa/packaging.git",
        rev="23.2",
        files=(
            ("_structures", [[5, 61]]),
            ("version", [[17, 563]]),
            ("utils", [[54, 100]]),
            ("specifiers", [[28, 1030]]),
        ),
        basepath=Path(__file__).parent / "packaging/src/packaging",
        prefix="""
# MODIFIED FROM https://github.com/pypa/packaging
# see repo for original licenses
# This software is made available under the terms of *either* of the licenses
# found in LICENSE.APACHE or LICENSE.BSD. Contributions to this software is made
# under the terms of *both* these licenses.
""",
        imports="""
import abc  # noqa
import itertools  # noqa
import re  # noqa
from typing import (  # noqa
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Set,
    SupportsInt,
    Tuple,
    TypeVar,
    Union,
)
""",
        suffix="""
Version = v_packaging_Version
SpecifierSet = v_packaging_SpecifierSet
""",
    ),
    Package(
        name="tomli",
        url="https://github.com/hukkin/tomli.git",
        # rev="2.0.1",
        rev="a6138675bcca68eea5b8abec7c2ec06d57f965a0",
        files=(
            ("_types", [[7, 11]]),
            ("_re", [[14, 107]]),
            ("_parser", [[20, 691]]),
        ),
        prefix="""
if sys.version_info >= (3, 11):
    from tomllib import loads as toml_loads
else:
    # MODIFIED FROM https://github.com/hukkin/tomli
    # see below for original license
    # SPDX-License-Identifier: MIT
    # SPDX-FileCopyrightText: 2021 Taneli Hukkinen
    # Licensed to PSF under a Contributor Agreement.
""",
        imports="""
    import string  # noqa
    from collections.abc import Iterable  # noqa
    from functools import lru_cache  # noqa
    from datetime import date, datetime, time, timedelta, timezone, tzinfo  # noqa
    from types import MappingProxyType  # noqa
    from typing import IO, Any, Callable, NamedTuple  # noqa
""",
        basepath=Path(__file__).parent / "tomli/src/tomli",
        suffix="""
    toml_loads = v_tomli_loads
""",
        indent=True,
    ),
]


def main():
    viv_source_path = Path(__file__).parent.parent / "src/viv/viv.py"
    viv_source = viv_source_path.read_text()

    for pkg in PACKAGES:
        viv_source = pkg.insert(viv_source)

    viv_source_path.write_text(viv_source)


if __name__ == "__main__":
    main()
