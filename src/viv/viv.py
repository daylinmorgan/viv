#!/usr/bin/env python3
"""viv isn't venv!

  viv -h
    OR
  __import__("viv").use("requests", "bs4")
"""

from __future__ import annotations

import hashlib
import itertools
import json
import logging
import os
import platform
import re
import shutil
import site
import subprocess
import sys
import tempfile
import threading
import venv
from argparse import (
    SUPPRESS,
    Action,
    HelpFormatter,
    Namespace,
    RawDescriptionHelpFormatter,
    _SubParsersAction,
)
from argparse import ArgumentParser as StdArgParser
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from textwrap import dedent, fill
from time import sleep
from types import TracebackType
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NoReturn,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Type,
    Union,
)

__version__ = "2023.1003-pep723"


##### START VENDORED TOMLI #####
# MODIFIED FROM https://github.com/hukkin/tomli
# see below for original license
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2021 Taneli Hukkinen
# Licensed to PSF under a Contributor Agreement.


import string  # noqa
from collections.abc import Iterable  # noqa
from functools import lru_cache  # noqa
from datetime import date, datetime, time, timedelta, timezone, tzinfo  # noqa
from types import MappingProxyType  # noqa
from typing import IO, Any, Callable, NamedTuple  # noqa

ParseFloat = Callable[[str], Any]
Key = Tuple[str, ...]
Pos = int
# - 00:32:00.999999
# - 00:32:00
__tomli___TIME_RE_STR = (
    r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])(?:\.([0-9]{1,6})[0-9]*)?"
)
__tomli__RE_NUMBER = re.compile(
    r"""
0
(?:
    x[0-9A-Fa-f](?:_?[0-9A-Fa-f])*   # hex
    |
    b[01](?:_?[01])*                 # bin
    |
    o[0-7](?:_?[0-7])*               # oct
)
|
[+-]?(?:0|[1-9](?:_?[0-9])*)         # dec, integer part
(?P<floatpart>
    (?:\.[0-9](?:_?[0-9])*)?         # optional fractional part
    (?:[eE][+-]?[0-9](?:_?[0-9])*)?  # optional exponent part
)
""",
    flags=re.VERBOSE,
)
__tomli__RE_LOCALTIME = re.compile(__tomli___TIME_RE_STR)
__tomli__RE_DATETIME = re.compile(
    rf"""
([0-9]{{4}})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])  # date, e.g. 1988-10-27
(?:
    [Tt ]
    {__tomli___TIME_RE_STR}
    (?:([Zz])|([+-])([01][0-9]|2[0-3]):([0-5][0-9]))?  # optional time offset
)?
""",
    flags=re.VERBOSE,
)


def __tomli__match_to_datetime(match: re.Match) -> datetime | date:
    """Convert a `__tomli__RE_DATETIME` match to `datetime.datetime` or `datetime.date`.
    Raises ValueError if the match does not correspond to a valid date
    or datetime.
    """
    (
        year_str,
        month_str,
        day_str,
        hour_str,
        minute_str,
        sec_str,
        micros_str,
        zulu_time,
        offset_sign_str,
        offset_hour_str,
        offset_minute_str,
    ) = match.groups()
    year, month, day = int(year_str), int(month_str), int(day_str)
    if hour_str is None:
        return date(year, month, day)
    hour, minute, sec = int(hour_str), int(minute_str), int(sec_str)
    micros = int(micros_str.ljust(6, "0")) if micros_str else 0
    if offset_sign_str:
        tz: tzinfo | None = __tomli__cached_tz(
            offset_hour_str, offset_minute_str, offset_sign_str
        )
    elif zulu_time:
        tz = timezone.utc
    else:  # local date-time
        tz = None
    return datetime(year, month, day, hour, minute, sec, micros, tzinfo=tz)


@lru_cache(maxsize=None)
def __tomli__cached_tz(hour_str: str, minute_str: str, sign_str: str) -> timezone:
    sign = 1 if sign_str == "+" else -1
    return timezone(
        timedelta(
            hours=sign * int(hour_str),
            minutes=sign * int(minute_str),
        )
    )


def __tomli__match_to_localtime(match: re.Match) -> time:
    hour_str, minute_str, sec_str, micros_str = match.groups()
    micros = int(micros_str.ljust(6, "0")) if micros_str else 0
    return time(int(hour_str), int(minute_str), int(sec_str), micros)


def __tomli__match_to_number(match: re.Match, parse_float: ParseFloat) -> Any:
    if match.group("floatpart"):
        return parse_float(match.group())
    return int(match.group(), 0)


__tomli__ASCII_CTRL = frozenset(chr(i) for i in range(32)) | frozenset(chr(127))
# Neither of these sets include quotation mark or backslash. They are
# currently handled as separate cases in the parser functions.
__tomli__ILLEGAL_BASIC_STR_CHARS = __tomli__ASCII_CTRL - frozenset("\t")
__tomli__ILLEGAL_MULTILINE_BASIC_STR_CHARS = __tomli__ASCII_CTRL - frozenset("\t\n")
__tomli__ILLEGAL_LITERAL_STR_CHARS = __tomli__ILLEGAL_BASIC_STR_CHARS
__tomli__ILLEGAL_MULTILINE_LITERAL_STR_CHARS = (
    __tomli__ILLEGAL_MULTILINE_BASIC_STR_CHARS
)
__tomli__ILLEGAL_COMMENT_CHARS = __tomli__ILLEGAL_BASIC_STR_CHARS
__tomli__TOML_WS = frozenset(" \t")
__tomli__TOML_WS_AND_NEWLINE = __tomli__TOML_WS | frozenset("\n")
__tomli__BARE_KEY_CHARS = frozenset(string.ascii_letters + string.digits + "-_")
__tomli__KEY_INITIAL_CHARS = __tomli__BARE_KEY_CHARS | frozenset("\"'")
__tomli__HEXDIGIT_CHARS = frozenset(string.hexdigits)
__tomli__BASIC_STR_ESCAPE_REPLACEMENTS = MappingProxyType(
    {
        "\\b": "\u0008",  # backspace
        "\\t": "\u0009",  # tab
        "\\n": "\u000A",  # linefeed
        "\\f": "\u000C",  # form feed
        "\\r": "\u000D",  # carriage return
        '\\"': "\u0022",  # quote
        "\\\\": "\u005C",  # backslash
    }
)


class TOMLDecodeError(ValueError):
    """An error raised if a document is not valid TOML."""


def __tomli__load(
    __fp: IO[bytes], *, parse_float: ParseFloat = float
) -> dict[str, Any]:
    """Parse TOML from a binary file object."""
    b = __fp.read()
    try:
        s = b.decode()
    except AttributeError:
        raise TypeError(
            "File must be opened in binary mode, e.g. use `open('foo.toml', 'rb')`"
        ) from None
    return __tomli__loads(s, parse_float=parse_float)


def __tomli__loads(
    __s: str, *, parse_float: ParseFloat = float
) -> dict[str, Any]:  # noqa: C901
    """Parse TOML from a string."""
    # The spec allows converting "\r\n" to "\n", even in string
    # literals. Let's do so to simplify parsing.
    src = __s.replace("\r\n", "\n")
    pos = 0
    out = Output(NestedDict(), Flags())
    header: Key = ()
    parse_float = __tomli__make_safe_parse_float(parse_float)
    # Parse one statement at a time
    # (typically means one line in TOML source)
    while True:
        # 1. Skip line leading whitespace
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
        # 2. Parse rules. Expect one of the following:
        #    - end of file
        #    - end of line
        #    - comment
        #    - key/value pair
        #    - append dict to list (and move to its namespace)
        #    - create dict (and move to its namespace)
        # Skip trailing whitespace when applicable.
        try:
            char = src[pos]
        except IndexError:
            break
        if char == "\n":
            pos += 1
            continue
        if char in __tomli__KEY_INITIAL_CHARS:
            pos = __tomli__key_value_rule(src, pos, out, header, parse_float)
            pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
        elif char == "[":
            try:
                second_char: str | None = src[pos + 1]
            except IndexError:
                second_char = None
            out.flags.finalize_pending()
            if second_char == "[":
                pos, header = __tomli__create_list_rule(src, pos, out)
            else:
                pos, header = __tomli__create_dict_rule(src, pos, out)
            pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
        elif char != "#":
            raise __tomli__suffixed_err(src, pos, "Invalid statement")
        # 3. Skip comment
        pos = __tomli__skip_comment(src, pos)
        # 4. Expect end of line or end of file
        try:
            char = src[pos]
        except IndexError:
            break
        if char != "\n":
            raise __tomli__suffixed_err(
                src, pos, "Expected newline or end of document after a statement"
            )
        pos += 1
    return out.data.dict


class Flags:
    """Flags that map to parsed keys/namespaces."""

    # Marks an immutable namespace (inline array or inline table).
    FROZEN = 0
    # Marks a nest that has been explicitly created and can no longer
    # be opened using the "[table]" syntax.
    EXPLICIT_NEST = 1

    def __init__(self) -> None:
        self._flags: dict[str, dict] = {}
        self._pending_flags: set[tuple[Key, int]] = set()

    def add_pending(self, key: Key, flag: int) -> None:
        self._pending_flags.add((key, flag))

    def finalize_pending(self) -> None:
        for key, flag in self._pending_flags:
            self.set(key, flag, recursive=False)
        self._pending_flags.clear()

    def unset_all(self, key: Key) -> None:
        cont = self._flags
        for k in key[:-1]:
            if k not in cont:
                return
            cont = cont[k]["nested"]
        cont.pop(key[-1], None)

    def set(self, key: Key, flag: int, *, recursive: bool) -> None:  # noqa: A003
        cont = self._flags
        key_parent, key_stem = key[:-1], key[-1]
        for k in key_parent:
            if k not in cont:
                cont[k] = {"flags": set(), "recursive_flags": set(), "nested": {}}
            cont = cont[k]["nested"]
        if key_stem not in cont:
            cont[key_stem] = {"flags": set(), "recursive_flags": set(), "nested": {}}
        cont[key_stem]["recursive_flags" if recursive else "flags"].add(flag)

    def is_(self, key: Key, flag: int) -> bool:
        if not key:
            return False  # document root has no flags
        cont = self._flags
        for k in key[:-1]:
            if k not in cont:
                return False
            inner_cont = cont[k]
            if flag in inner_cont["recursive_flags"]:
                return True
            cont = inner_cont["nested"]
        key_stem = key[-1]
        if key_stem in cont:
            cont = cont[key_stem]
            return flag in cont["flags"] or flag in cont["recursive_flags"]
        return False


class NestedDict:
    def __init__(self) -> None:
        # The parsed content of the TOML document
        self.dict: dict[str, Any] = {}

    def get_or_create_nest(
        self,
        key: Key,
        *,
        access_lists: bool = True,
    ) -> dict:
        cont: Any = self.dict
        for k in key:
            if k not in cont:
                cont[k] = {}
            cont = cont[k]
            if access_lists and isinstance(cont, list):
                cont = cont[-1]
            if not isinstance(cont, dict):
                raise KeyError("There is no nest behind this key")
        return cont

    def append_nest_to_list(self, key: Key) -> None:
        cont = self.get_or_create_nest(key[:-1])
        last_key = key[-1]
        if last_key in cont:
            list_ = cont[last_key]
            if not isinstance(list_, list):
                raise KeyError("An object other than list found behind this key")
            list_.append({})
        else:
            cont[last_key] = [{}]


class Output(NamedTuple):
    data: NestedDict
    flags: Flags


def __tomli__skip_chars(src: str, pos: Pos, chars: Iterable[str]) -> Pos:
    try:
        while src[pos] in chars:
            pos += 1
    except IndexError:
        pass
    return pos


def __tomli__skip_until(
    src: str,
    pos: Pos,
    expect: str,
    *,
    error_on: frozenset[str],
    error_on_eof: bool,
) -> Pos:
    try:
        new_pos = src.index(expect, pos)
    except ValueError:
        new_pos = len(src)
        if error_on_eof:
            raise __tomli__suffixed_err(src, new_pos, f"Expected {expect!r}") from None
    if not error_on.isdisjoint(src[pos:new_pos]):
        while src[pos] not in error_on:
            pos += 1
        raise __tomli__suffixed_err(src, pos, f"Found invalid character {src[pos]!r}")
    return new_pos


def __tomli__skip_comment(src: str, pos: Pos) -> Pos:
    try:
        char: str | None = src[pos]
    except IndexError:
        char = None
    if char == "#":
        return __tomli__skip_until(
            src,
            pos + 1,
            "\n",
            error_on=__tomli__ILLEGAL_COMMENT_CHARS,
            error_on_eof=False,
        )
    return pos


def __tomli__skip_comments_and_array_ws(src: str, pos: Pos) -> Pos:
    while True:
        pos_before_skip = pos
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS_AND_NEWLINE)
        pos = __tomli__skip_comment(src, pos)
        if pos == pos_before_skip:
            return pos


def __tomli__create_dict_rule(src: str, pos: Pos, out: Output) -> tuple[Pos, Key]:
    pos += 1  # Skip "["
    pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
    pos, key = __tomli__parse_key(src, pos)
    if out.flags.is_(key, Flags.EXPLICIT_NEST) or out.flags.is_(key, Flags.FROZEN):
        raise __tomli__suffixed_err(src, pos, f"Cannot declare {key} twice")
    out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
    try:
        out.data.get_or_create_nest(key)
    except KeyError:
        raise __tomli__suffixed_err(src, pos, "Cannot overwrite a value") from None
    if not src.startswith("]", pos):
        raise __tomli__suffixed_err(
            src, pos, "Expected ']' at the end of a table declaration"
        )
    return pos + 1, key


def __tomli__create_list_rule(src: str, pos: Pos, out: Output) -> tuple[Pos, Key]:
    pos += 2  # Skip "[["
    pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
    pos, key = __tomli__parse_key(src, pos)
    if out.flags.is_(key, Flags.FROZEN):
        raise __tomli__suffixed_err(
            src, pos, f"Cannot mutate immutable namespace {key}"
        )
    # Free the namespace now that it points to another empty list item...
    out.flags.unset_all(key)
    # ...but this key precisely is still prohibited from table declaration
    out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
    try:
        out.data.append_nest_to_list(key)
    except KeyError:
        raise __tomli__suffixed_err(src, pos, "Cannot overwrite a value") from None
    if not src.startswith("]]", pos):
        raise __tomli__suffixed_err(
            src, pos, "Expected ']]' at the end of an array declaration"
        )
    return pos + 2, key


def __tomli__key_value_rule(
    src: str, pos: Pos, out: Output, header: Key, parse_float: ParseFloat
) -> Pos:
    pos, key, value = __tomli__parse_key_value_pair(src, pos, parse_float)
    key_parent, key_stem = key[:-1], key[-1]
    abs_key_parent = header + key_parent
    relative_path_cont_keys = (header + key[:i] for i in range(1, len(key)))
    for cont_key in relative_path_cont_keys:
        # Check that dotted key syntax does not redefine an existing table
        if out.flags.is_(cont_key, Flags.EXPLICIT_NEST):
            raise __tomli__suffixed_err(
                src, pos, f"Cannot redefine namespace {cont_key}"
            )
        # Containers in the relative path can't be opened with the table syntax or
        # dotted key/value syntax in following table sections.
        out.flags.add_pending(cont_key, Flags.EXPLICIT_NEST)
    if out.flags.is_(abs_key_parent, Flags.FROZEN):
        raise __tomli__suffixed_err(
            src, pos, f"Cannot mutate immutable namespace {abs_key_parent}"
        )
    try:
        nest = out.data.get_or_create_nest(abs_key_parent)
    except KeyError:
        raise __tomli__suffixed_err(src, pos, "Cannot overwrite a value") from None
    if key_stem in nest:
        raise __tomli__suffixed_err(src, pos, "Cannot overwrite a value")
    # Mark inline table and array namespaces recursively immutable
    if isinstance(value, (dict, list)):
        out.flags.set(header + key, Flags.FROZEN, recursive=True)
    nest[key_stem] = value
    return pos


def __tomli__parse_key_value_pair(
    src: str, pos: Pos, parse_float: ParseFloat
) -> tuple[Pos, Key, Any]:
    pos, key = __tomli__parse_key(src, pos)
    try:
        char: str | None = src[pos]
    except IndexError:
        char = None
    if char != "=":
        raise __tomli__suffixed_err(
            src, pos, "Expected '=' after a key in a key/value pair"
        )
    pos += 1
    pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
    pos, value = __tomli__parse_value(src, pos, parse_float)
    return pos, key, value


def __tomli__parse_key(src: str, pos: Pos) -> tuple[Pos, Key]:
    pos, key_part = __tomli__parse_key_part(src, pos)
    key: Key = (key_part,)
    pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
    while True:
        try:
            char: str | None = src[pos]
        except IndexError:
            char = None
        if char != ".":
            return pos, key
        pos += 1
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
        pos, key_part = __tomli__parse_key_part(src, pos)
        key += (key_part,)
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)


def __tomli__parse_key_part(src: str, pos: Pos) -> tuple[Pos, str]:
    try:
        char: str | None = src[pos]
    except IndexError:
        char = None
    if char in __tomli__BARE_KEY_CHARS:
        start_pos = pos
        pos = __tomli__skip_chars(src, pos, __tomli__BARE_KEY_CHARS)
        return pos, src[start_pos:pos]
    if char == "'":
        return __tomli__parse_literal_str(src, pos)
    if char == '"':
        return __tomli__parse_one_line_basic_str(src, pos)
    raise __tomli__suffixed_err(src, pos, "Invalid initial character for a key part")


def __tomli__parse_one_line_basic_str(src: str, pos: Pos) -> tuple[Pos, str]:
    pos += 1
    return __tomli__parse_basic_str(src, pos, multiline=False)


def __tomli__parse_array(
    src: str, pos: Pos, parse_float: ParseFloat
) -> tuple[Pos, list]:
    pos += 1
    array: list = []
    pos = __tomli__skip_comments_and_array_ws(src, pos)
    if src.startswith("]", pos):
        return pos + 1, array
    while True:
        pos, val = __tomli__parse_value(src, pos, parse_float)
        array.append(val)
        pos = __tomli__skip_comments_and_array_ws(src, pos)
        c = src[pos : pos + 1]
        if c == "]":
            return pos + 1, array
        if c != ",":
            raise __tomli__suffixed_err(src, pos, "Unclosed array")
        pos += 1
        pos = __tomli__skip_comments_and_array_ws(src, pos)
        if src.startswith("]", pos):
            return pos + 1, array


def __tomli__parse_inline_table(
    src: str, pos: Pos, parse_float: ParseFloat
) -> tuple[Pos, dict]:
    pos += 1
    nested_dict = NestedDict()
    flags = Flags()
    pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
    if src.startswith("}", pos):
        return pos + 1, nested_dict.dict
    while True:
        pos, key, value = __tomli__parse_key_value_pair(src, pos, parse_float)
        key_parent, key_stem = key[:-1], key[-1]
        if flags.is_(key, Flags.FROZEN):
            raise __tomli__suffixed_err(
                src, pos, f"Cannot mutate immutable namespace {key}"
            )
        try:
            nest = nested_dict.get_or_create_nest(key_parent, access_lists=False)
        except KeyError:
            raise __tomli__suffixed_err(src, pos, "Cannot overwrite a value") from None
        if key_stem in nest:
            raise __tomli__suffixed_err(
                src, pos, f"Duplicate inline table key {key_stem!r}"
            )
        nest[key_stem] = value
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
        c = src[pos : pos + 1]
        if c == "}":
            return pos + 1, nested_dict.dict
        if c != ",":
            raise __tomli__suffixed_err(src, pos, "Unclosed inline table")
        if isinstance(value, (dict, list)):
            flags.set(key, Flags.FROZEN, recursive=True)
        pos += 1
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)


def __tomli__parse_basic_str_escape(
    src: str, pos: Pos, *, multiline: bool = False
) -> tuple[Pos, str]:
    escape_id = src[pos : pos + 2]
    pos += 2
    if multiline and escape_id in {"\\ ", "\\\t", "\\\n"}:
        # Skip whitespace until next non-whitespace character or end of
        # the doc. Error if non-whitespace is found before newline.
        if escape_id != "\\\n":
            pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS)
            try:
                char = src[pos]
            except IndexError:
                return pos, ""
            if char != "\n":
                raise __tomli__suffixed_err(src, pos, "Unescaped '\\' in a string")
            pos += 1
        pos = __tomli__skip_chars(src, pos, __tomli__TOML_WS_AND_NEWLINE)
        return pos, ""
    if escape_id == "\\u":
        return __tomli__parse_hex_char(src, pos, 4)
    if escape_id == "\\U":
        return __tomli__parse_hex_char(src, pos, 8)
    try:
        return pos, __tomli__BASIC_STR_ESCAPE_REPLACEMENTS[escape_id]
    except KeyError:
        raise __tomli__suffixed_err(src, pos, "Unescaped '\\' in a string") from None


def __tomli__parse_basic_str_escape_multiline(src: str, pos: Pos) -> tuple[Pos, str]:
    return __tomli__parse_basic_str_escape(src, pos, multiline=True)


def __tomli__parse_hex_char(src: str, pos: Pos, hex_len: int) -> tuple[Pos, str]:
    hex_str = src[pos : pos + hex_len]
    if len(hex_str) != hex_len or not __tomli__HEXDIGIT_CHARS.issuperset(hex_str):
        raise __tomli__suffixed_err(src, pos, "Invalid hex value")
    pos += hex_len
    hex_int = int(hex_str, 16)
    if not __tomli__is_unicode_scalar_value(hex_int):
        raise __tomli__suffixed_err(
            src, pos, "Escaped character is not a Unicode scalar value"
        )
    return pos, chr(hex_int)


def __tomli__parse_literal_str(src: str, pos: Pos) -> tuple[Pos, str]:
    pos += 1  # Skip starting apostrophe
    start_pos = pos
    pos = __tomli__skip_until(
        src, pos, "'", error_on=__tomli__ILLEGAL_LITERAL_STR_CHARS, error_on_eof=True
    )
    return pos + 1, src[start_pos:pos]  # Skip ending apostrophe


def __tomli__parse_multiline_str(
    src: str, pos: Pos, *, literal: bool
) -> tuple[Pos, str]:
    pos += 3
    if src.startswith("\n", pos):
        pos += 1
    if literal:
        delim = "'"
        end_pos = __tomli__skip_until(
            src,
            pos,
            "'''",
            error_on=__tomli__ILLEGAL_MULTILINE_LITERAL_STR_CHARS,
            error_on_eof=True,
        )
        result = src[pos:end_pos]
        pos = end_pos + 3
    else:
        delim = '"'
        pos, result = __tomli__parse_basic_str(src, pos, multiline=True)
    # Add at maximum two extra apostrophes/quotes if the end sequence
    # is 4 or 5 chars long instead of just 3.
    if not src.startswith(delim, pos):
        return pos, result
    pos += 1
    if not src.startswith(delim, pos):
        return pos, result + delim
    pos += 1
    return pos, result + (delim * 2)


def __tomli__parse_basic_str(src: str, pos: Pos, *, multiline: bool) -> tuple[Pos, str]:
    if multiline:
        error_on = __tomli__ILLEGAL_MULTILINE_BASIC_STR_CHARS
        parse_escapes = __tomli__parse_basic_str_escape_multiline
    else:
        error_on = __tomli__ILLEGAL_BASIC_STR_CHARS
        parse_escapes = __tomli__parse_basic_str_escape
    result = ""
    start_pos = pos
    while True:
        try:
            char = src[pos]
        except IndexError:
            raise __tomli__suffixed_err(src, pos, "Unterminated string") from None
        if char == '"':
            if not multiline:
                return pos + 1, result + src[start_pos:pos]
            if src.startswith('"""', pos):
                return pos + 3, result + src[start_pos:pos]
            pos += 1
            continue
        if char == "\\":
            result += src[start_pos:pos]
            pos, parsed_escape = parse_escapes(src, pos)
            result += parsed_escape
            start_pos = pos
            continue
        if char in error_on:
            raise __tomli__suffixed_err(src, pos, f"Illegal character {char!r}")
        pos += 1


def __tomli__parse_value(  # noqa: C901
    src: str, pos: Pos, parse_float: ParseFloat
) -> tuple[Pos, Any]:
    try:
        char: str | None = src[pos]
    except IndexError:
        char = None
    # IMPORTANT: order conditions based on speed of checking and likelihood
    # Basic strings
    if char == '"':
        if src.startswith('"""', pos):
            return __tomli__parse_multiline_str(src, pos, literal=False)
        return __tomli__parse_one_line_basic_str(src, pos)
    # Literal strings
    if char == "'":
        if src.startswith("'''", pos):
            return __tomli__parse_multiline_str(src, pos, literal=True)
        return __tomli__parse_literal_str(src, pos)
    # Booleans
    if char == "t":
        if src.startswith("true", pos):
            return pos + 4, True
    if char == "f":
        if src.startswith("false", pos):
            return pos + 5, False
    # Arrays
    if char == "[":
        return __tomli__parse_array(src, pos, parse_float)
    # Inline tables
    if char == "{":
        return __tomli__parse_inline_table(src, pos, parse_float)
    # Dates and times
    datetime_match = __tomli__RE_DATETIME.match(src, pos)
    if datetime_match:
        try:
            datetime_obj = __tomli__match_to_datetime(datetime_match)
        except ValueError as e:
            raise __tomli__suffixed_err(src, pos, "Invalid date or datetime") from e
        return datetime_match.end(), datetime_obj
    localtime_match = __tomli__RE_LOCALTIME.match(src, pos)
    if localtime_match:
        return localtime_match.end(), __tomli__match_to_localtime(localtime_match)
    # Integers and "normal" floats.
    # The regex will greedily match any type starting with a decimal
    # char, so needs to be located after handling of dates and times.
    number_match = __tomli__RE_NUMBER.match(src, pos)
    if number_match:
        return number_match.end(), __tomli__match_to_number(number_match, parse_float)
    # Special floats
    first_three = src[pos : pos + 3]
    if first_three in {"inf", "nan"}:
        return pos + 3, parse_float(first_three)
    first_four = src[pos : pos + 4]
    if first_four in {"-inf", "+inf", "-nan", "+nan"}:
        return pos + 4, parse_float(first_four)
    raise __tomli__suffixed_err(src, pos, "Invalid value")


def __tomli__suffixed_err(src: str, pos: Pos, msg: str) -> TOMLDecodeError:
    """Return a `TOMLDecodeError` where error message is suffixed with
    coordinates in source."""

    def coord_repr(src: str, pos: Pos) -> str:
        if pos >= len(src):
            return "end of document"
        line = src.count("\n", 0, pos) + 1
        if line == 1:
            column = pos + 1
        else:
            column = pos - src.rindex("\n", 0, pos)
        return f"line {line}, column {column}"

    return TOMLDecodeError(f"{msg} (at {coord_repr(src, pos)})")


def __tomli__is_unicode_scalar_value(codepoint: int) -> bool:
    return (0 <= codepoint <= 55295) or (57344 <= codepoint <= 1114111)


def __tomli__make_safe_parse_float(parse_float: ParseFloat) -> ParseFloat:
    """A decorator to make `parse_float` safe.
    `parse_float` must not return dicts or lists, because these types
    would be mixed with parsed TOML tables and arrays, thus confusing
    the parser. The returned decorated callable raises `ValueError`
    instead of returning illegal types.
    """
    # The default `float` callable never returns illegal types. Optimize it.
    if parse_float is float:
        return float

    def safe_parse_float(float_str: str) -> Any:
        float_value = parse_float(float_str)
        if isinstance(float_value, (dict, list)):
            raise ValueError("parse_float must not return dicts or lists")
        return float_value

    return safe_parse_float


##### END VENDORED TOMLI #####


# fmt: on


# fmt: on


class Spinner:
    """spinner modified from:
    https://raw.githubusercontent.com/Tagar/stuff/master/spinner.py
    """

    def __init__(self, message: str, delay: float = 0.1) -> None:
        self.spinner = itertools.cycle([f"{c}  " for c in "⣾⣽⣻⢿⡿⣟⣯⣷"])
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        self.message = message
        sys.stderr.write(f"{a.prefix} {a.sep} {message} ")

    def write_next(self) -> None:
        with self._screen_lock:
            if not self.spinner_visible:
                sys.stderr.write(next(self.spinner))
                self.spinner_visible = True
                sys.stderr.flush()

    def remove_spinner(self, cleanup: bool = False) -> None:
        with self._screen_lock:
            if self.spinner_visible:
                sys.stderr.write("\b\b\b")
                self.spinner_visible = False
                if cleanup:
                    sys.stderr.write("   ")  # overwrite spinner with blank
                    sys.stderr.write("\r\033[K")
                sys.stderr.flush()

    def spinner_task(self) -> None:
        while self.busy:
            self.write_next()
            sleep(self.delay)
            self.remove_spinner()

    def __enter__(self) -> None:
        if sys.stderr.isatty():
            self._screen_lock = threading.Lock()
            self.busy = True
            self.thread = threading.Thread(target=self.spinner_task)
            self.thread.start()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        if sys.stderr.isatty():
            self.busy = False
            self.remove_spinner(cleanup=True)
        else:
            sys.stderr.write("\r")


def _path_ok(p: Path) -> Path:
    p.mkdir(exist_ok=True, parents=True)
    return p


class Env:
    defaults = dict(
        viv_bin_dir=Path.home() / ".local" / "bin",
        xdg_cache_home=Path.home() / ".cache",
        xdg_data_home=Path.home() / ".local" / "share",
    )

    def __getattr__(self, attr: str) -> Any:
        if (
            not attr.startswith("_")
            and (defined := getattr(self, f"_{attr}")) is not None
        ):
            return defined
        else:
            return os.getenv(attr.upper(), self.defaults.get(attr))

    @property
    def _viv_cache(self) -> Path:
        return Path(os.getenv("VIV_CACHE", (Path(self.xdg_cache_home) / "viv")))

    @property
    def _viv_spec(self) -> List[str]:
        return [i[1:-1] for i in os.getenv("VIV_SPEC", "").split(" ") if i]

    @property
    def _viv_log_path(self) -> Path:
        return _path_ok(Path(self.xdg_data_home) / "viv") / "viv.log"

    @property
    def _viv_run_mode(self) -> str:
        choices = {"ephemeral", "semi-ephemeral", "persist"}
        run_mode = os.getenv("VIV_RUN_MODE", "ephemeral")
        if run_mode not in choices:
            err_quit(
                f"unsupported VIV_RUN_MODE: {run_mode} \noptions: "
                + ", ".join(
                    (f"{a.bold}{a.yellow}{choice}{a.end}" for choice in choices)
                )
            )
        return run_mode


class System:
    def __init__(self) -> None:
        self._windows = platform.system() == "Windows"
        (self.bin_dir, *_) = ("Scripts",) if self._windows else ("bin",)

    def bin(self, exe: str) -> str:
        return f"{exe}.exe" if self._windows else exe


system = System()


class Cfg:
    def __init__(self) -> None:
        self.windows = platform.system() == "Windows"

    @property
    def src(self) -> Path:
        p = Path(Env().xdg_data_home) / "viv" / "viv.py"
        p.parent.mkdir(exist_ok=True, parents=True)
        return p

    @property
    def cache_base(self) -> Path:
        return Env().viv_cache

    @property
    def cache_src(self) -> Path:
        return _path_ok(self.cache_base / "src")

    @property
    def cache_venv(self) -> Path:
        return _path_ok(self.cache_base / "venvs")


class Ansi:
    """control ouptut of ansi(VT100) control codes"""

    def __init__(self) -> None:
        self.bold = "\033[1m"
        self.dim = "\033[2m"
        self.underline = "\033[4m"
        self.red = "\033[1;31m"
        self.green = "\033[1;32m"
        self.yellow = "\033[1;33m"
        self.magenta = "\033[1;35m"
        self.cyan = "\033[1;36m"
        self.end = "\033[0m"

        # for argparse help
        self.header = self.cyan
        self.option = self.yellow
        self.metavar = "\033[33m"  # normal yellow

        if not Env().force_color and (Env().no_color or not sys.stderr.isatty()):
            for attr in self.__dict__:
                setattr(self, attr, "")

        self._ansi_escape = re.compile(
            r"""
            \x1B  # ESC
            (?:   # 7-bit C1 Fe (except CSI)
                [@-Z\\-_]
            |     # or [ for CSI, followed by a control sequence
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
            """,
            re.VERBOSE,
        )

        self.sep = f"{self.magenta}|{self.end}"
        self.prefix = f"{self.cyan}viv{self.end}"

    def escape(self, txt: str) -> str:
        return self._ansi_escape.sub("", txt)

    def style(self, txt: str, style: str = "cyan") -> str:
        """style text with given style
        Args:
            txt: text to stylize
            style: color/style to apply to text
        Returns:
            ansi escape code stylized text
        """
        return f"{getattr(self,style)}{txt}{getattr(self,'end')}"

    def tagline(self) -> str:
        """generate the viv tagline"""

        return " ".join(
            (
                self.style(f, "magenta") + self.style(rest, "cyan")
                for f, rest in (("v", "iv"), ("i", "sn't"), ("v", "env"))
            )
        )

    def key_value(self, items: Dict[str, Any], indent: str = "  ") -> None:
        for k, v in items.items():
            sys.stderr.write(f"{indent}{a.bold}{k}{a.end}: {v}\n")

    def subprocess(self, command: List[str], output: str) -> None:
        """generate output for subprocess error

        Args:
            output: text output from subprocess, usually from p.stdout
        """
        if not output:
            return

        log.error("subprocess failed")
        log.error("see below for command output")
        log.error(f"cmd:\n  {' '.join(command)}")
        new_output = [f"{self.red}->{self.end} {line}" for line in output.splitlines()]
        log.error("subprocess output:" + "\n".join(("", *new_output, "")))


a = Ansi()


class MutlilineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        outlines = []
        lines = (save_msg := record.msg).splitlines()
        for line in lines:
            record.msg = line
            outlines.append(super().format(record))
        record.msg = save_msg
        record.message = (output := "\n".join(outlines))
        return output


class CustomFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__()
        self.FORMATS = {
            **{
                level: " ".join(
                    (
                        a.prefix,
                        f"{a.sep}{color}%(levelname)s{a.end}{a.sep}",
                        "%(message)s",
                    )
                )
                for level, color in {
                    logging.DEBUG: a.dim,
                    logging.WARNING: a.yellow,
                    logging.ERROR: a.red,
                    logging.CRITICAL: a.red,
                }.items()
            },
            logging.INFO: f"{a.prefix} {a.sep} %(message)s",
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = MutlilineFormatter(log_fmt)
        return formatter.format(record)


class CustomFileHandler(RotatingFileHandler):
    """Custom logging handler to strip ansi before logging to file"""

    def emit(self, record: logging.LogRecord) -> None:
        record.msg = a.escape(record.msg)
        super().emit(record)


def gen_logger() -> logging.Logger:
    logger = logging.getLogger("viv")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO if not Env().viv_debug else logging.DEBUG)
        ch.setFormatter(CustomFormatter())

        fh = CustomFileHandler(
            Env().viv_log_path, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            MutlilineFormatter("%(asctime)s | %(levelname)8s | %(message)s")
        )

        logger.addHandler(ch)
        logger.addHandler(fh)
    return logger


log = gen_logger()


def err_quit(*msg: str, code: int = 1) -> NoReturn:
    log.error("\n".join(msg))
    sys.exit(code)


class Template:
    _standalone_func = r"""def _viv_use(*pkgs, track_exe=False, name=""):
    import hashlib, json, os, site, shutil, sys, venv  # noqa
    from pathlib import Path  # noqa
    from datetime import datetime  # noqa
    from subprocess import run  # noqa

    if not {*map(type, pkgs)} == {str}:
        raise ValueError(f"spec: {pkgs} is invalid")

    meta = dict.fromkeys(("created", "accessed"), (t := str(datetime.today())))
    runner = str(Path(__file__).absolute().resolve())
    envvar = lambda x: os.getenv(f"VIV_{x}")  # noqa
    nopkgs = lambda p: not p.endswith(("dist-packages", "site-packages"))  # noqa
    F, V, no_st = map(envvar, ("FORCE", "VERBOSE", "NO_SETUPTOOLS"))
    base = Path(xdg) if (xdg := os.getenv("XDG_CACHE_HOME")) else Path.home() / ".cache"
    (cache := (base) / "viv/venvs").mkdir(parents=True, exist_ok=True)
    exe = str(Path(sys.executable).resolve()) if track_exe else "N/A"
    _id = hashlib.sha256((str(spec := [*pkgs]) + exe).encode()).hexdigest()
    if (env := cache / (name if name else _id[:8])) not in cache.glob("*/") or F:
        sys.stderr.write(f"generating new vivenv -> {env.name}\n")
        venv.create(env, prompt=f"viv-{name}", symlinks=True, clear=True)
        kw = dict(zip(("stdout", "stderr"), ((None,) * 2 if V else (-1, 2))))
        cmd = ["pip", "--python", str(env / "bin" / "python"), "install", *spec]
        if (not no_st) and (not [x for x in spec if x.startswith("setuptools")]):
            cmd.append("setuptools")
        p = run(cmd, **kw)
        if (rc := p.returncode) != 0:
            if env.is_dir():
                shutil.rmtree(env)
            sys.stderr.write(f"pip had non zero exit ({rc})\n{p.stdout.decode()}\n")
            sys.exit(rc)
        meta.update(dict(id=_id, spec=spec, exe=exe, name=name, files=[runner]))
    else:
        meta = json.loads((env / "vivmeta.json").read_text())
        meta.update(dict(accessed=t, files=sorted({*meta["files"], runner})))
    (env / "vivmeta.json").write_text(json.dumps(meta))
    site.addsitedir(sitepkgs := str(*(env / "lib").glob("py*/si*")))
    sys.path = [sitepkgs, *filter(nopkgs, sys.path)]

    return env
"""

    @staticmethod
    def description(name: str) -> str:
        return f"""

{a.tagline()}
command line: `{a.bold}viv run typer rich-click -s ./script.py{a.end}`
python api: {a.style('__import__("viv").use("typer", "rich-click")','bold')}
"""

    @staticmethod
    def noqa(txt: str) -> str:
        max_length = max(map(len, txt.splitlines()))
        return "\n".join((f"{line:{max_length}} # noqa" for line in txt.splitlines()))

    @staticmethod
    def _use_str(spec: List[str], standalone: bool = False) -> str:
        spec_str = ", ".join(f'"{req}"' for req in spec)
        if standalone:
            return f"""_viv_use({fill(spec_str,width=90,subsequent_indent="    ",)})"""
        else:
            return f"""__import__("viv").use({spec_str})"""

    @classmethod
    def standalone(cls, spec: List[str]) -> str:
        func_use = "\n".join(
            (cls._standalone_func, cls.noqa(cls._use_str(spec, standalone=True)))
        )
        return f"""
# AUTOGENERATED by viv (v{__version__})
# see `python3 <(curl -fsSL viv.dayl.in/viv.py) --help`

{func_use}
"""

    @staticmethod
    def _rel_import(local_source: Optional[Path]) -> str:
        if not local_source:
            raise ValueError("local source must exist")

        path_to_viv = path_to_viv = str(
            local_source.resolve().absolute().parent
        ).replace(str(Path.home()), "~")
        return (
            """__import__("sys").path.append(__import__("os")"""
            f""".path.expanduser("{path_to_viv}"))  # noqa"""
        )

    @staticmethod
    def _absolute_import(local_source: Optional[Path]) -> str:
        if not local_source:
            raise ValueError("local source must exist")

        path_to_viv = local_source.resolve().absolute().parent
        return f"""__import__("sys").path.append("{path_to_viv}")  # noqa"""

    @classmethod
    def frozen_import(
        cls, path: str, local_source: Optional[Path], spec: List[str]
    ) -> str:
        if path == "abs":
            imports = cls._absolute_import(local_source)
        elif path == "rel":
            imports = cls._rel_import(local_source)
        else:
            imports = ""
        return f"""\
{imports}
{cls.noqa(cls._use_str(spec))}
"""

    @classmethod
    def shim(
        cls,
        path: str,
        local_source: Optional[Path],
        standalone: bool,
        spec: List[str],
        bin: str,
    ) -> str:
        if standalone:
            imports = cls._standalone_func
        elif path == "abs":
            imports = cls._absolute_import(local_source)
        elif path == "rel":
            imports = cls._rel_import(local_source)
        else:
            imports = ""
        return f"""\
#!/usr/bin/env python3
# AUTOGENERATED by viv (v{__version__})
# see `python3 <(curl -fsSL viv.dayl.in/viv.py) --help`


{imports}

import subprocess
import sys

if __name__ == "__main__":
    vivenv = {cls.noqa(cls._use_str(spec, standalone))}
    sys.exit(subprocess.run([vivenv / "bin" / "{bin}", *sys.argv[1:]]).returncode)
"""

    @staticmethod
    def update(
        src: Optional[Path], cli: Path, local_version: str, next_version: str
    ) -> str:
        return f"""
  Update source at {a.green}{src}{a.end}
  Symlink {a.bold}{src}{a.end} to {a.bold}{cli}{a.end}
  Version {a.bold}{local_version}{a.end} -> {a.bold}{next_version}{a.end}

"""

    @staticmethod
    def install(src: Path, cli: Path) -> str:
        return f"""
  Install viv.py to {a.green}{src}{a.end}
  Symlink {a.bold}{src}{a.end} to {a.bold}{cli}{a.end}

"""


# TODO: convert the below functions into a proper file/stream logging interface
def echo(
    msg: str, style: str = "magenta", newline: bool = True, fd: TextIO = sys.stderr
) -> None:
    """output general message to stdout"""
    output = f"{a.prefix} {a.sep} {msg}\n"
    fd.write(output)


def error(*msg: str, exit: bool = True, code: int = 1) -> None:
    """output error message and if code provided exit"""
    prefix = f"{a.prefix} {a.sep}{a.red}ERROR{a.end}{a.sep} "
    sys.stderr.write("\n".join((f"{prefix}{line}" for line in msg)) + "\n")
    if exit:
        sys.exit(code)


def confirm(question: str, context: str = "", yes: bool = False) -> bool:
    sys.stderr.write(context)
    # TODO: update this
    sys.stderr.write(
        f"{a.prefix} {a.sep}{a.magenta}?{a.end}{a.sep}"
        f" {question} {a.yellow}(Y)es/(n)o{a.end} "
    )
    if yes:
        sys.stderr.write(f"{a.green}[FORCED YES]{a.end}\n")
        return True

    while True:
        ans = input().strip().lower()
        if ans in ("y", "yes"):
            return True
        elif ans in ("n", "no"):
            return False
        sys.stderr.write("Please select (Y)es or (n)o. ")
    sys.stderr.write("\n")


class CustomHelpFormatter(RawDescriptionHelpFormatter, HelpFormatter):
    """formatter to remove extra metavar on short opts"""

    def _get_invocation_length(self, invocation: str) -> int:
        return len(a.escape(invocation))

    def _format_action_invocation(self, action: Action) -> str:
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return a.style(metavar, style="option")
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(
                    [
                        a.style(option, style="option")
                        for option in action.option_strings
                    ]
                )

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            # change to
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                parts.extend(
                    [
                        a.style(option, style="option")
                        for option in action.option_strings
                    ]
                )
                # add metavar to last string
                parts[-1] += a.style(f" {args_string}", style="metavar")
            return (", ").join(parts)

    def _format_usage(self, *args: Any, **kwargs: Any) -> str:
        formatted_usage = super()._format_usage(*args, **kwargs)
        # patch usage with color formatting
        formatted_usage = (
            formatted_usage
            if f"{a.header}usage{a.end}:" in formatted_usage
            else formatted_usage.replace("usage:", f"{a.header}usage{a.end}:")
        )
        return formatted_usage

    def _format_action(self, action: Action) -> str:
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent
        action_header = self._format_action_invocation(action)
        action_header_len = len(a.escape(action_header))

        # no help; start on same line and add a final newline
        if not action.help:
            action_header = "%*s%s\n" % (self._current_indent, "", action_header)
        # short action name; start on the same line and pad two spaces
        elif action_header_len <= action_width:
            # tup = self._current_indent, "", action_width, action_header
            action_header = (
                f"{' '*self._current_indent}{action_header}"
                f"{' '*(action_width+2 - action_header_len)}"
            )
            indent_first = 0

        # long action name; start on the next line
        else:
            action_header = "%*s%s\n" % (self._current_indent, "", action_header)
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help and action.help.strip():
            help_text = self._expand_help(action)
            if help_text:
                help_lines = self._split_lines(help_text, help_width)
                parts.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                for line in help_lines[1:]:
                    parts.append("%*s%s\n" % (help_position, "", line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith("\n"):
            parts.append("\n")

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def start_section(self, heading: Optional[str]) -> None:
        if heading:
            super().start_section(a.style(heading, style="header"))
        else:
            super()

    def add_argument(self, action: Action) -> None:
        if action.help is not SUPPRESS:
            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length accounting for ansi codes
            invocation_length = max(map(self._get_invocation_length, invocations))
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])


class KVAppendAction(Action):
    def __init__(self, *args: Any, keys: List[str], **kwargs: Any) -> None:
        self._keys = keys
        super(KVAppendAction, self).__init__(*args, **kwargs)

    def __call__(
        self,
        parser: StdArgParser,
        namespace: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            raise TypeError("expected string for `values`")
        try:
            (k, v) = values.split(":")
            if k not in self._keys:
                err_quit(
                    "".join(
                        (
                            f"unexpected key: {a.yellow}{k}{a.end} for {self.dest},",
                            " must be one of: ",
                            ", ".join((a.style(k, "bold") for k in self._keys)),
                        )
                    )
                )
            d = {k: v}
        except ValueError:
            err_quit(
                f"failed to parse key-value for {self.dest} "
                f'"{a.bold}{values}{a.end}" as k:v'
            )
        items = getattr(namespace, self.dest)
        if not items:
            items = {}

        items.update(d)
        setattr(namespace, self.dest, items)


class ArgumentParser(StdArgParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.formatter_class = lambda prog: CustomHelpFormatter(
            prog,
            max_help_position=35,
        )

    def error(self, message: str) -> NoReturn:
        error(message, f"see `{a.bold}{self.prog} --help{a.end}` for more info")
        sys.exit(2)


def subprocess_run(
    command: List[str],
    spinmsg: str = "",
    clean_up_path: Optional[Path] = None,
    verbose: bool = False,
    ignore_error: bool = False,
    check_output: bool = False,
) -> str:
    """run a subcommand

    Args:
        command: Subcommand to be run in subprocess.
        verbose: If true, print subcommand output.
    """

    log.debug("executing subcmd:\n  " + " ".join(command))

    if spinmsg and not verbose:
        with Spinner(spinmsg):
            p = subprocess.run(
                command,
                stdout=None if verbose else subprocess.PIPE,
                stderr=None if verbose else subprocess.STDOUT,
                universal_newlines=True,
            )
    else:
        p = subprocess.run(
            command,
            stdout=None if verbose else subprocess.PIPE,
            stderr=None if verbose else subprocess.STDOUT,
            universal_newlines=True,
        )

    if p.returncode != 0 and not ignore_error:
        a.subprocess(command, p.stdout)

        if clean_up_path and clean_up_path.is_dir():
            shutil.rmtree(str(clean_up_path))

        sys.exit(p.returncode)

    if not verbose:
        log.debug(
            "output:\n" + "\n".join(f"-> {line}" for line in p.stdout.splitlines())
        )

    if check_output:
        return p.stdout

    else:
        return ""


def subprocess_run_quit(command: List[str | Path], **kwargs: Any) -> None:
    log.debug("executing subcmd:\n  " + " ".join(map(str, command)))
    sys.exit(subprocess.run(command, **kwargs).returncode)


def get_hash(spec: Tuple[str, ...] | List[str], track_exe: bool = False) -> str:
    """generate a hash of package specifications

    Args:
        spec: sequence of package specifications
        track_exe: if true add python executable to hash
    Returns:
        sha256 representation of dependencies for vivenv
    """

    return hashlib.sha256(
        (
            str(spec) + (str(Path(sys.executable).resolve()) if track_exe else "N/A")
        ).encode()
    ).hexdigest()


def _get_user() -> str:
    """good-faith attempt to ascertain user name for viv cache"""
    from getpass import getuser, GetPassWarning  # noqa

    try:
        user = getuser()

    except ImportError as e:
        user = "dummy"
        log.info(e.msg)
        log.info("failed to get user with getpass.getuser", "using `dummy` as fallback")
    return user


class Meta:
    def __init__(
        self,
        name: str,
        id: str,
        spec: List[str],
        files: List[str],
        exe: str,
        created: str = "",
        accessed: str = "",
    ):
        self.name = name
        self.id = id
        self.spec = spec
        self.files = files
        self.exe = exe
        self.created = created
        self.accessed = accessed

    @classmethod
    def load(cls, name: str) -> "Meta":
        if not (Cfg().cache_venv / name / "vivmeta.json").exists():
            log.warning(f"possibly corrupted vivenv: {name}")
            # add empty values for corrupted vivenvs so it will still load
            return cls(name=name, spec=[""], files=[""], exe="", id="")
        else:
            meta = json.loads((Cfg().cache_venv / name / "vivmeta.json").read_text())

        return cls(**meta)

    def write(self, p: Path | None = None) -> None:
        if not p:
            p = (Cfg().cache_venv) / self.name / "vivmeta.json"

        p.write_text(json.dumps(self.__dict__))

    def addfile(self, f: Path) -> None:
        log.debug(f"associating {f} with {self.name}")
        self.accessed = str(datetime.today())
        self.files = sorted({*self.files, str(f.absolute().resolve())})


class ViVenv:
    def __init__(
        self,
        spec: List[str] = [""],
        track_exe: bool = False,
        id: str | None = None,
        name: str = "",
        path: Path | None = None,
        skip_load: bool = False,
        metadata: Meta | None = None,
        skip_validation: bool = False,
    ) -> None:
        self.loaded = False
        if not skip_validation:
            spec = self._validate_spec(spec)
        id = id if id else get_hash(spec, track_exe)

        self.name = name if name else id[:8]
        self.set_path(path)

        if not metadata:
            if self.name in (d.name for d in Cfg().cache_venv.iterdir()):
                self.loaded = True
                self.meta = Meta.load(self.name)
            else:
                self.meta = Meta(
                    spec=spec,
                    name=self.name,
                    id=id,
                    files=[],
                    exe=str(Path(sys.executable).resolve()) if track_exe else "N/A",
                )
        else:
            self.meta = metadata

    @classmethod
    def load(cls, name: str) -> "ViVenv":
        """generate a vivenv from a vivmeta.json
        Args:
            name: used as lookup in the vivenv cache
        """
        vivenv = cls(name=name, metadata=Meta.load(name))

        return vivenv

    def exists(self) -> None:
        if self.name in (d.name for d in Cfg().cache_venv.iterdir()):
            self.loaded = True

    def set_path(self, path: Path | None = None) -> None:
        self.path = path if path else Cfg().cache_venv / self.name
        self.python = str(
            (self.path / system.bin_dir / system.bin("python")).absolute()
        )
        self.pip = (system.bin("pip"), "--python", self.python)

    def _validate_spec(self, spec: List[str]) -> List[str]:
        """ensure spec is at least of sequence of strings

        Args:
            spec: sequence of package specifications
        """
        if not set(map(type, spec)) == {str}:
            err_quit(
                "unexepected input in package spec",
                f"check your packages definitions: {spec}",
            )

        return sorted(spec)

    def bin_exists(self, bin: str) -> None:
        if not (self.path / system.bin_dir / bin).is_file():
            message = f"{a.bold}{bin}{a.end} does not exist " "\nOptions:\n"

            message += "  " + " ".join(
                (
                    a.style(p.name, "bold")
                    for p in (self.path / system.bin_dir).iterdir()
                    if not p.name.lower().startswith("activate")
                )
            )
            err_quit(message)

    def create(self, quiet: bool = False) -> None:
        log.info(f"new unique vivenv: {a.bold}{self.name}{a.end}")
        log.debug(f"creating new venv at {self.path}")
        with Spinner("creating vivenv"):
            venv.create(
                self.path,
                prompt=f"viv-{self.name}",
                clear=True,
                symlinks=platform.system() != "Windows",
            )

        self.meta.created = str(datetime.today())

    def install_pkgs(self) -> None:
        cmd: List[str] = [
            *self.pip,
            "install",
            "--force-reinstall",
        ] + self.meta.spec

        if not Env().viv_no_setuptools and "setuptools" not in self.meta.spec:
            cmd.append("setuptools")

        subprocess_run(
            cmd,
            spinmsg="installing packages in vivenv",
            clean_up_path=self.path,
            verbose=bool(Env().viv_verbose),
        )

    def ensure(self) -> None:
        self.exists()
        if not self.loaded or Env().viv_force:
            self.create()
            self.install_pkgs()

    def touch(self) -> None:
        self.meta.accessed = str(datetime.today())

    @property
    def site_packages(self) -> str:
        return str(*(self.path / "lib").glob("python*/site-packages"))

    def activate(self) -> None:
        # also add sys.path here so that it comes first
        log.debug(f"activating {self.name}")
        path_to_add = self.site_packages

        # approximate behavior of python -S
        sys.path = [
            path_to_add,
            *(
                p
                for p in sys.path
                if not p.endswith(("dist-packages", "site-packages"))
            ),
        ]
        site.addsitedir(path_to_add)

    def files_exist(self) -> bool:
        return len([f for f in self.meta.files if Path(f).is_file()]) == 0

    def get_size(self) -> None:
        size = float(
            sum(p.stat().st_size for p in Path(self.path).rglob("*") if p.is_file())
        )
        for unit in ("", "K", "M", "G", "T"):
            if size < 1024:
                break
            size /= 1024

        self.size = f"{size:.1f}{unit}B"

    @contextmanager
    def use(self, keep: bool = True) -> Generator[None, None, None]:
        run_mode = Env().viv_run_mode
        _path = self.path

        def common() -> None:
            self.ensure()
            self.touch()

        try:
            if self.loaded or keep or run_mode == "persist":
                common()
                yield
            elif run_mode == "ephemeral":
                with tempfile.TemporaryDirectory(prefix="viv-") as tmpdir:
                    self.set_path(Path(tmpdir))
                    common()
                    yield
            elif run_mode == "semi-ephemeral":
                ephemeral_cache = _path_ok(
                    Path(tempfile.gettempdir()) / f"viv-ephemeral-cache-{_get_user()}"
                )
                os.environ.update(dict(VIV_CACHE=str(ephemeral_cache)))
                self.set_path(ephemeral_cache / "venvs" / self.name)
                common()
                yield
        finally:
            self.set_path(_path)

    def show(self, size_pad: int) -> None:
        _id = (
            self.meta.id[:8]
            if self.meta.id == self.name
            else (self.name[:5] + "..." if len(self.name) > 8 else self.name)
        )
        size = getattr(self, "size", None)
        line = []
        if size:
            line.append(f"""{a.yellow}{size:>{size_pad}}{a.end}""")

        line.extend(
            (
                f"""{a.bold}{a.cyan}{_id}{a.end}""",
                f"""{a.style(", ".join(self.meta.spec),'dim')}""",
            )
        )
        sys.stdout.write(" ".join(line) + "\n")

    def _tree_leaves(self, items: List[str], indent: str = "") -> str:
        tree_chars = ["├"] * (len(items) - 1) + ["╰"]
        return "\n".join(
            (f"{indent}{a.yellow}{c}─{a.end} {i}" for c, i in zip(tree_chars, items))
        )

    def tree(self) -> None:
        items = [
            f"{a.magenta}{k}{a.end}: {v}"
            for k, v in {
                **{
                    "id": self.meta.id,
                    "spec": ", ".join(self.meta.spec),
                    "created": self.meta.created,
                    "accessed": self.meta.accessed,
                },
                **(
                    {"size": getattr(self, "size", None)}
                    if getattr(self, "size", None)
                    else {}
                ),
                **({"exe": self.meta.exe} if self.meta.exe != "N/A" else {}),
                **({"files": ""} if self.meta.files else {}),
            }.items()
        ]
        rows = [f"\n{a.bold}{a.cyan}{self.name}{a.end}", self._tree_leaves(items)]
        if self.meta.files:
            rows += (self._tree_leaves(self.meta.files, indent="   "),)

        sys.stdout.write("\n".join(rows) + "\n")


def get_caller_path() -> Path:
    """get callers callers file path"""
    # viv.py is fist in stack since function is used in `viv.use()`
    import inspect  # noqa

    frame_info = inspect.stack()[2]
    filepath = frame_info.filename  # in python 3.5+, you can use frame_info.filename
    del frame_info  # drop the reference to the stack frame to avoid reference cycles

    return Path(filepath).absolute()


def use(*packages: str, track_exe: bool = False, name: str = "") -> Path:
    """create a vivenv and append to sys.path

    Args:
        packages: package specifications with optional version specifiers
        track_exe: if true make env python exe specific
        name: use as vivenv name, if not provided id is used
    """

    vivenv = ViVenv([*list(packages), *Env().viv_spec], track_exe=track_exe, name=name)
    with vivenv.use():
        vivenv.meta.addfile(get_caller_path())
        vivenv.meta.write()
        vivenv.activate()

    return vivenv.path


def combined_spec(reqs: List[str], requirements: Path) -> List[str]:
    if requirements:
        with requirements.open("r") as f:
            reqs += f.readlines()
    return reqs


def resolve_deps(reqs: List[str], requirements: Path) -> List[str]:
    spec = combined_spec(reqs, requirements)

    cmd = [
        system.bin("pip"),
        "install",
        "--dry-run",
        "--quiet",
        "--ignore-installed",
        "--disable-pip-version-check",
        "--report",
        "-",
    ] + spec
    try:
        result = subprocess_run(cmd, check_output=True, spinmsg="resolving depedencies")
        report = json.loads(result)
    except json.JSONDecodeError:
        err_quit(
            f"failed to parse result from cmd: {a.bold}{' '.join(cmd)}{a.end}\n"
            "see viv log for output"
        )

    resolved_spec = [
        f"{pkg['metadata']['name']}=={pkg['metadata']['version']}"
        for pkg in report["install"]
    ]

    return resolved_spec


def fetch_script(url: str) -> str:
    from urllib.error import HTTPError  # noqa
    from urllib.request import urlopen  # noqa

    try:
        log.debug(f"fetching from remote url: {url}")
        r = urlopen(url)
    except (HTTPError, ValueError) as e:
        err_quit(
            "Failed to fetch from remote url:",
            f"  {a.bold}{url}{a.end}",
            "see below:" + a.style("->  ", "red").join(["\n"] + repr(e).splitlines()),
        )

    return r.read().decode("utf-8")


def fetch_source(reference: str) -> str:
    src = fetch_script(
        "https://raw.githubusercontent.com/daylinmorgan/viv/"
        + reference
        + "/src/viv/viv.py"
    )

    sha256 = hashlib.sha256(src.encode()).hexdigest()

    cached_src_file = Cfg().cache_src / f"{sha256}.py"

    if not cached_src_file.is_file():
        log.debug("updating source script")
        cached_src_file.write_text(src)

    return sha256


def make_executable(path: Path) -> None:
    """apply an executable bit for all users with read access"""
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2  # copy R bits to X
    os.chmod(path, mode)


def uses_viv(txt: str) -> bool:
    return bool(
        re.search(
            r"""
            ^(?!\#)\s*
            (?:__import__\(\s*["']viv["']\s*\))
            |
            (?:from\ viv\ import\ use)
            |
            (?:import\ viv)
        """,
            txt,
            re.VERBOSE | re.MULTILINE,
        )
    )


METADATA_BLOCK = (
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
)


def read_metadata_block(script: str) -> dict | None:
    name = "pyproject"
    matches = list(
        filter(lambda m: m.group("type") == name, re.finditer(METADATA_BLOCK, script))
    )
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        return __tomli__loads(
            "\n".join((line[2:] for line in matches[0].group(0).splitlines()[1:-1]))
        )
    else:
        return None


# DEPENDENCY_BLOCK_MARKER = r"(?i)^#\s+script\s+dependencies:\s*$"
#
# def read_dependency_block(txt: str) -> Generator[str, None, None]:
#     lines = iter(txt.splitlines())
#     for line in lines:
#         if re.match(DEPENDENCY_BLOCK_MARKER, line):
#             for line in lines:
#                 if not line.startswith("#"):
#                     break
#                 # Remove comments. An inline comment is introduced by
#                 # a hash, which must be preceded and followed by a
#                 # space. The initial hash will be skipped as it has
#                 # no space before it.
#                 line = line.split(" # ", maxsplit=1)[0]
#                 line = line[1:].strip()
#                 if not line:
#                     continue
#                 # let pip handle the requirement errors
#                 yield line
#             break
#


def _parse_date(txt: str) -> datetime:
    """attempt to parse datetime string

    acceptable formats `%Y-%m-%d` & `%Y-%m-%dT%H:%M`
    """

    try:
        date = datetime.strptime(
            txt,
            "%Y-%m-%d",
        )
        return date
    except ValueError:
        pass

    try:
        date = datetime.strptime(txt, "%Y-%m-%dT%H:%M")
        return date
    except ValueError:
        pass

    err_quit(
        f"failed to parse {a.yellow}{txt}{a.end} as datetime\n"
        "acceptable formats `%Y-%m-%d` & `%Y-%m-%dT%H:%M`"
    )


class Cache:
    def __init__(self) -> None:
        self.vivenvs = self._get_venvs()

    def _get_venvs(self, cache_dir: Path = Cfg().cache_venv) -> Set[ViVenv]:
        return {ViVenv.load(p.name) for p in cache_dir.iterdir()}

    @staticmethod
    def _compare_dates(
        vivenv: ViVenv, date_name: str, when: str, date: datetime
    ) -> bool:
        vivenv_date = datetime.strptime(
            getattr(vivenv.meta, date_name), "%Y-%m-%d %H:%M:%S.%f"
        )
        if when == "before":
            return vivenv_date < date
        else:
            return vivenv_date > date

    def _filter_date(self, date_name: str, when: str, date: datetime) -> Set[ViVenv]:
        return {
            vivenv
            for vivenv in self.vivenvs
            if self._compare_dates(
                vivenv,
                date_name,
                when,
                date,
            )
        }

    def _filter_file(self, file: str) -> Set[ViVenv]:
        if file == "None":
            return {vivenv for vivenv in self.vivenvs if vivenv.files_exist()}
        else:
            p = Path(file).absolute().resolve()
            if not p.is_file():
                err_quit(f"Unable to find local file: {file}")
            return {vivenv for vivenv in self.vivenvs if str(p) in vivenv.meta.files}

    def _filter_spec(self, spec: str) -> Set[ViVenv]:
        return {
            vivenv for vivenv in self.vivenvs if spec in ", ".join(vivenv.meta.spec)
        }

    def filter(self, filters: Dict[str, str]) -> Set[ViVenv]:
        vivenv_sets = []

        for k, v in filters.items():
            if "-" in k:  # date-based filters all have hyphen
                (date_name, when) = k.split("-")
                vivenv_sets.append(self._filter_date(date_name, when, _parse_date(v)))
            elif k == "files":
                vivenv_sets.append(self._filter_file(v))

            elif k == "spec":
                vivenv_sets.append(self._filter_spec(v))

        if vivenv_sets:
            return {vivenv for vivenv in set.union(*vivenv_sets)}
        else:
            return set()


class Viv:
    def __init__(self) -> None:
        self.t = Template()
        self._cache = Cache()
        self._get_sources()
        self.name = "viv" if self.local else "python3 <(curl -fsSL viv.dayl.in/viv.py)"

    def _get_sources(self) -> None:
        self.local_source: Optional[Path] = None
        self.running_source = Path(__file__).resolve()
        self.local = not str(self.running_source).startswith("/proc/")
        try:
            # prevent running `viv` from being imported
            curr = sys.path[0]
            sys.path = sys.path[1:]
            _local_viv = __import__("viv")
            sys.path.insert(0, curr)

            if _local_viv.__file__:
                self.local_source = Path(_local_viv.__file__)
                self.local_version = _local_viv.__version__
            else:
                self.local_version = "Not Found"
        except ImportError:
            self.local_version = "Not Found"

        if self.local_source:
            self.git = (self.local_source.parent.parent.parent / ".git").is_dir()
        else:
            self.git = False

    def _match_vivenv(self, name_id: str) -> ViVenv:  # type: ignore[return]
        matches: List[ViVenv] = []
        vivenvs = self._cache.vivenvs

        for vivenv in vivenvs:
            if name_id == vivenv.meta.id:
                matches.append(vivenv)
            elif vivenv.name == name_id:
                matches.append(vivenv)
            elif vivenv.name.startswith(name_id) or (
                vivenv.meta.id.startswith(name_id) and vivenv.meta.id == vivenv.name
            ):
                matches.append(vivenv)
            elif vivenv.name.startswith(name_id):
                matches.append(vivenv)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            err_quit(
                "matches: " + ",".join((match.name for match in matches)),
                "too many matches maybe try a longer name?",
            )
        else:
            err_quit(f"no matches found for {name_id}")

    def cmd_env(self) -> None:
        """manage the viv vivenv cache"""

    def cmd_env_remove(self, vivenvs: List[str]) -> None:
        """\
        remove a vivenv

        To remove all viv venvs:
        `viv cache remove $(viv l -q)`
        """

        for name in vivenvs:
            vivenv = self._match_vivenv(name)
            if vivenv.path.is_dir():
                with Spinner(f"removing vivenv {a.bold}{vivenv.name}{a.end}"):
                    shutil.rmtree(vivenv.path)
                log.info(f"{a.bold}{vivenv.name}{a.end} succesfully removed")
            else:
                err_quit(
                    f"cowardly exiting because I didn't find vivenv: {name}",
                )

    def cmd_freeze(
        self,
        reqs: List[str],
        requirements: Path,
        keep: bool,
        standalone: bool,
        path: str,
    ) -> None:
        """create import statement from package spec"""

        spec = resolve_deps(reqs, requirements)
        if keep:
            vivenv = ViVenv(spec)
            with vivenv.use():
                vivenv.touch()
                vivenv.meta.write()

        log.info("see below for import statements\n")

        if standalone:
            sys.stdout.write(self.t.standalone(spec))
            return

        if path and not self.local_source:
            err_quit("No local viv found to import from")

        sys.stdout.write(self.t.frozen_import(path, self.local_source, spec))

    def cmd_list(
        self,
        quiet: bool,
        verbose: bool,
        use_json: bool,
        filter: Dict[str, str],
        size: bool,
    ) -> None:
        """\
        list vivenvs

        examples:
          `viv list \\
              --filter "accessed-after:2023-08-01"`
          `viv list -q --filter \\
            "created-before:$(date -d '2 weeks ago' +'%Y-%m-%d')"`
          `viv list --filter "files:./script.py"`
          `viv list --filter "files:None"`
        """

        if filter:
            vivenvs = self._cache.filter(filter)
        else:
            vivenvs = self._cache.vivenvs

        if quiet:
            sys.stdout.write("\n".join((vivenv.meta.id for vivenv in vivenvs)) + "\n")
            sys.exit(0)

        # NOTE: this feels out of place
        size_pad = 0
        if size:
            for vivenv in vivenvs:
                vivenv.get_size()
                size_pad = max(size_pad, len(vivenv.size))

        if len(self._cache.vivenvs) == 0:
            log.info("no vivenvs setup")
        elif len(vivenvs) == 0 and filter:
            log.info("no vivenvs match filter")
        elif verbose:
            for vivenv in vivenvs:
                vivenv.tree()
        elif use_json:
            sys.stdout.write(
                json.dumps({vivenv.name: vivenv.meta.__dict__ for vivenv in vivenvs})
            )
        else:
            for vivenv in vivenvs:
                vivenv.show(size_pad)

    def cmd_env_exe(self, vivenv_id: str, cmd: str, rest: List[str]) -> None:
        """\
        run binary/script in existing vivenv

        examples:
            viv exe <vivenv> python -- script.py
            viv exe <vivenv> python -- -m http.server
        """

        vivenv = self._match_vivenv(vivenv_id)
        bin = vivenv.path / "bin" / cmd
        vivenv.bin_exists(bin.name)
        full_cmd = [str(bin), *rest]

        # TODO: use subprocess_run_quit
        subprocess_run(full_cmd, verbose=True)

    def cmd_env_info(
        self, vivenv_id: str, path: bool, use_json: bool, size: bool
    ) -> None:
        """get metadata about a vivenv"""
        vivenv = self._match_vivenv(vivenv_id)
        metadata_file = vivenv.path / "vivmeta.json"

        if not metadata_file.is_file():
            err_quit(f"Unable to find metadata for vivenv: {vivenv_id}")
        if size:
            vivenv.get_size()
        if use_json:
            sys.stdout.write(json.dumps(vivenv.meta.__dict__))
        elif path:
            sys.stdout.write(f"{vivenv.path.absolute()}\n")
        else:
            vivenv.tree()

    def _install_local_src(self, sha256: str, src: Path, cli: Path, yes: bool) -> None:
        log.info("updating local source copy of viv")
        shutil.copy(Cfg().cache_src / f"{sha256}.py", src)
        make_executable(src)
        log.info("symlinking cli")

        if cli.is_file():
            log.info(f"Existing file at {a.style(str(cli),'bold')}")
            if confirm("Would you like to overwrite it?", yes=yes):
                cli.unlink()
                cli.symlink_to(src)
        else:
            cli.parent.mkdir(exist_ok=True, parents=True)
            cli.symlink_to(src)

        log.info("Remember to include the following line in your shell rc file:")
        sys.stderr.write(
            '  export PYTHONPATH="$PYTHONPATH:$HOME/'
            f'{src.relative_to(Path.home()).parent}"\n'
        )

    def _get_new_version(self, ref: str) -> Tuple[str, str]:
        sys.path.append(str(Cfg().cache_src))
        return (sha256 := fetch_source(ref)), __import__(sha256).__version__

    def cmd_manage(self) -> None:
        """manage viv itself"""

    def cmd_manage_show(
        self,
        pythonpath: bool = False,
        system: bool = False,
    ) -> None:
        """manage viv itself"""
        if pythonpath:
            if self.local and self.local_source:
                sys.stdout.write(str(self.local_source.parent) + "\n")
            else:
                err_quit("expected to find a local installation")
        else:
            echo(f"{a.yellow}Current{a.end}:")
            a.key_value(
                {
                    "Version": __version__,
                    "CLI": shutil.which("viv"),
                    "Running Source": self.running_source,
                    "Local Source": self.local_source,
                    "Cache": Cfg().cache_base,
                }
            )

            if system:
                echo(f"{a.yellow}System{a.end}:")
                a.key_value(
                    {
                        "Python Exe": sys.executable,
                        "Python Version": sys.version,
                        "Pip": subprocess_run(
                            ["pip", "--version"], check_output=True
                        ).strip(),
                    }
                )

    def cmd_manage_update(
        self,
        ref: str,
        src: Path,
        cli: Path,
        yes: bool,
    ) -> None:
        sha256, next_version = self._get_new_version(ref)

        if self.local_version == next_version:
            log.info(f"no change between {ref} and local version")
            sys.exit(0)

        if confirm(
            "Would you like to perform the above installation steps?",
            self.t.update(self.local_source, cli, self.local_version, next_version),
            yes=yes,
        ):
            self._install_local_src(
                sha256,
                Path(
                    src if not self.local_source else self.local_source,
                ),
                cli,
                yes,
            )

    def cmd_manage_install(
        self,
        ref: str,
        src: Path,
        cli: Path,
        yes: bool,
    ) -> None:
        sha256, downloaded_version = self._get_new_version(ref)

        log.info(f"Downloaded version: {downloaded_version}")

        # TODO: see if file is actually where
        # we are about to install and give more instructions

        if confirm(
            "Would you like to perform the above installation steps?",
            self.t.install(src, cli),
            yes=yes,
        ):
            self._install_local_src(sha256, src, cli, yes)

    def cmd_manage_purge(
        self,
        ref: str,
        src: Path,
        cli: Path,
        yes: bool,
    ) -> None:
        to_remove = []
        if Cfg().cache_base.is_dir():
            to_remove.append(Cfg().cache_base)
        if src.is_file():
            to_remove.append(src.parent if src == (Cfg().src) else src)
        if self.local_source and self.local_source.is_file():
            if self.local_source.parent.name == "viv":
                to_remove.append(self.local_source.parent)
            else:
                to_remove.append(self.local_source)

        if cli.is_file():
            to_remove.append(cli)

        to_remove = list(set(to_remove))
        if confirm(
            "Remove the above files/directories?",
            "\n".join(f"  - {a.red}{p}{a.end}" for p in to_remove) + "\n",
            yes=yes,
        ):
            for p in to_remove:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

            log.info(
                "to re-install use: "
                "`python3 <(curl -fsSL viv.dayl.in/viv.py) manage install`"
            )

    def _pick_bin(self, reqs: List[str], bin: str) -> Tuple[str, str]:
        default = system.bin(re.split(r"[=><~!*]+", reqs[0])[0])
        return default, (default if not bin else bin)

    def cmd_shim(
        self,
        reqs: List[str],
        requirements: Path,
        bin: str,
        output: Path,
        freeze: bool,
        yes: bool,
        path: str,
        standalone: bool,
    ) -> None:
        """\
        generate viv-powered cli apps

        examples:
          viv shim black
          viv shim yartsu -o ~/bin/yartsu --standalone
        """

        default_bin, bin = self._pick_bin(reqs, bin)
        output = Env().viv_bin_dir / default_bin if not output else output.absolute()

        if freeze:
            spec = resolve_deps(reqs, requirements)
        else:
            spec = combined_spec(reqs, requirements)

        if output.is_file():
            log.warning(f"{output} already exists")

        if confirm(
            f"Write shim for {a.bold}{bin}{a.end} to {a.green}{output}{a.end}?",
            yes=yes,
        ):
            output.parent.mkdir(exist_ok=True, parents=True)
            with output.open("w") as f:
                f.write(self.t.shim(path, self.local_source, standalone, spec, bin))
            make_executable(output)

    @staticmethod
    def _update_cache(env: os._Environ[str], keep: bool, tmpdir: str) -> None:
        run_mode = Env().viv_run_mode
        if not keep:
            if run_mode == "ephemeral":
                new_cache = tmpdir
            elif run_mode == "semi-ephemeral":
                new_cache = str(Path(tempfile.gettempdir()) / "viv-ephemeral-cache")

            env.update({"VIV_CACHE": new_cache})
            os.environ["VIV_CACHE"] = new_cache

    def _run_script(
        self, spec: List[str], script: str, keep: bool, rest: List[str]
    ) -> None:
        env = os.environ
        name = script.split("/")[-1]

        with tempfile.TemporaryDirectory(prefix="viv-") as tmpdir:
            tmppath = Path(tmpdir)

            if Path(script).is_file():
                scriptpath = Path(script).absolute()
                script_text = scriptpath.read_text()
            else:
                scriptpath = tmppath / name
                script_text = fetch_script(script)

            viv_used = uses_viv(script_text)
            deps = (
                read_metadata_block(script_text).get("run", {}).get("dependencies", [])
            )

            if viv_used and deps:
                error(
                    "Script Dependencies block and "
                    "`viv.use` API can't be used in the same script"
                )

            if not self.local_source and viv_used:
                log.debug("fetching remote copy to use for python api")
                (tmppath / "viv.py").write_text(
                    fetch_script(
                        "https://raw.githubusercontent.com/daylinmorgan/viv/latest/src/viv/viv.py"
                    )
                )

            scriptpath.write_text(script_text)
            self._update_cache(env, keep, tmpdir)

            if viv_used:
                log.debug(f"script invokes viv.use passing along spec: \n  '{spec}'")
                subprocess_run_quit(
                    [sys.executable, "-S", scriptpath, *rest],
                    env=dict(
                        env,
                        VIV_SPEC=" ".join(f"'{req}'" for req in spec),
                        PYTHONPATH=":".join((str(tmppath), env.get("PYTHONPATH", ""))),
                    ),
                )
            elif not spec and not deps:
                log.warning("using viv with empty spec, skipping vivenv creation")
                subprocess_run_quit([sys.executable, "-S", scriptpath, *rest])
            else:
                vivenv = ViVenv(spec + deps)
                with vivenv.use(keep=keep):
                    vivenv.meta.write()
                    subprocess_run_quit(
                        [vivenv.python, "-S", scriptpath, *rest],
                        env=dict(
                            env,
                            PYTHONPATH=":".join(
                                filter(None, (vivenv.site_packages, Env().pythonpath))
                            ),
                        ),
                    )

    def cmd_run(
        self,
        reqs: List[str],
        requirements: Path,
        script: str,
        keep: bool,
        rest: List[str],
        bin: str,
    ) -> None:
        """\
        run an app/script with an on-demand venv

        examples:
          viv r pycowsay -- "viv isn't venv\\!"
          viv r rich -b python -- -m rich
          viv r -s <python script>

        note: any args after `-s <python script>` will be passed on
        """

        spec = combined_spec(reqs, requirements)

        if script:
            self._run_script(spec, script, keep, rest)
        else:
            _, bin = self._pick_bin(reqs, bin)
            vivenv = ViVenv(spec)

            with vivenv.use(keep=keep):
                if keep or Env().viv_run_mode != "ephemeral":
                    vivenv.meta.write(vivenv.path / "vivmeta.json")

                vivenv.bin_exists(bin)
                subprocess_run_quit([vivenv.path / system.bin_dir / bin, *rest])


class Arg:
    def __init__(self, *args: Any, flag: str | None = None, **kwargs: Any) -> None:
        if flag:
            self.args: Tuple[Any, ...] = (f"-{flag[0]}", f"--{flag}")
        else:
            self.args = args
        self.kwargs = kwargs


class BoolArg(Arg):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(BoolArg, self).__init__(*args, action="store_true", **kwargs)


class PathArg(Arg):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(PathArg, self).__init__(*args, metavar="<path>", type=Path, **kwargs)


class Cli:
    args: Dict[Tuple[str, ...], List[Arg]] = {
        ("list",): [
            BoolArg(
                flag="verbose",
                help="pretty print full metadata for vivenvs",
            ),
            BoolArg(
                flag="quiet",
                help="show only ids",
            ),
            Arg(
                flag="filter",
                help="filter vivenvs based on key:val",
                metavar="<key:value>",
                action=KVAppendAction,
                keys=[
                    "created-before",
                    "created-after",
                    "accessed-before",
                    "accessed-after",
                    "files",
                    "spec",
                ],
            ),
        ],
        ("shim",): [
            BoolArg(
                flag="freeze",
                help="freeze/resolve all dependencies",
            ),
            PathArg(
                flag="output",
                help="path/to/output file",
            ),
        ],
        ("env_info",): [
            BoolArg(
                flag="path",
                help="print the absolute path to the vivenv",
            ),
        ],
        ("run",): [Arg(flag="script", help="script to execute", metavar="<path/url>")],
        ("env_exe", "env_info"): [
            Arg("vivenv_id", help="name/hash of vivenv", metavar="vivenv")
        ],
        ("list", "env_info"): [
            BoolArg(flag="size", help="calculate size of vivenvs"),
            BoolArg(
                "--json",
                help="name:metadata json for vivenvs ",
                default=False,
                dest="use_json",
            ),
        ],
        ("freeze", "shim"): [
            Arg(
                flag="path",
                help="generate line to add viv to sys.path",
                choices=["abs", "rel"],
            ),
            BoolArg(
                flag="standalone",
                help="generate standalone activation function",
            ),
        ],
        ("run", "freeze", "shim"): [
            Arg("reqs", help="requirements specifiers", nargs="*"),
            PathArg(
                flag="requirements",
                help="path/to/requirements.txt file",
            ),
        ],
        ("run", "freeze"): [
            BoolArg(
                flag="keep",
                help="preserve environment",
            ),
        ],
        ("run", "shim"): [
            Arg(flag="bin", help="console_script/script to invoke", metavar="<bin>"),
        ],
        ("manage_purge", "manage_update", "manage_install"): [
            Arg(
                flag="ref",
                help="git reference (branch/tag/commit)",
                default="latest",
                metavar="<ref>",
            ),
            PathArg(
                flag="src",
                help="path/to/source_file",
                default=Cfg().src,
            ),
            PathArg(
                flag="cli",
                help="path/to/cli (symlink to src)",
                default=Path.home() / ".local" / "bin" / "viv",
            ),
        ],
        ("shim", "manage_purge", "manage_update", "manage_install"): [
            BoolArg(flag="yes", help="respond yes to all prompts")
        ],
        ("manage_show",): [
            BoolArg(
                flag="pythonpath",
                help="show the path/to/install",
            ),
            BoolArg(flag="system", help="show system/python info too"),
        ],
        ("env_exe",): [
            Arg(
                "cmd",
                help="command to to execute",
            )
        ],
        ("env_remove",): [
            Arg("vivenvs", help="name/hash of vivenv", nargs="*", metavar="vivenv")
        ],
    }
    (
        cmds := dict.fromkeys(
            (
                "list",
                "shim",
                "run",
                "env",
                "freeze",
                "manage",
            )
        )
    ).update(
        {
            cmd: {
                subcmd: dict(description=help, help=help, aliases=[subcmd[0]])
                for subcmd, help in subcmd_help
            }
            for cmd, subcmd_help in (
                (
                    "env",
                    (
                        ("exe", "run binary/script in existing vivenv"),
                        ("info", "get metadata about a vivenv"),
                        ("remove", "remove a vivenv"),
                    ),
                ),
                (
                    "manage",
                    (
                        ("show", "show current installation"),
                        ("install", "install fresh viv"),
                        ("update", "update viv version"),
                        ("purge", "remove traces of viv"),
                    ),
                ),
            )
        }
    )

    def __init__(self, viv: Viv) -> None:
        self.viv = viv
        self.parser = ArgumentParser(
            prog=viv.name, description=viv.t.description(viv.name)
        )
        self._cmd_arg_group_map()
        self.parsers = self._make_parsers()
        self._add_args()

    def _cmd_arg_group_map(self) -> None:
        self.cmd_arg_group_map: Dict[str, List[Sequence[str] | str]] = {}
        for grp in self.args:
            if isinstance(grp, str):
                self.cmd_arg_group_map.setdefault(grp, []).append(grp)
            else:
                for cmd in grp:
                    self.cmd_arg_group_map.setdefault(cmd, []).append(grp)

    def _make_parsers(self) -> Dict[Sequence[str] | str, ArgumentParser]:
        return {**{grp: ArgumentParser(add_help=False) for grp in self.args}}

    def _add_args(self) -> None:
        for grp, args in self.args.items():
            for arg in args:
                self.parsers[grp].add_argument(*arg.args, **arg.kwargs)

    def _validate_args(self, args: Namespace) -> None:
        name = args.func.__name__.replace("cmd_", "")
        if name in ("freeze", "shim"):
            if not args.reqs:
                error("must specify a requirement")

            if not self.viv.local_source and not (args.standalone or args.path):
                log.warning(
                    "failed to find local copy of `viv` "
                    "make sure to add it to your PYTHONPATH "
                    "or consider using --path/--standalone"
                )

            # TODO: move this since this is code logic not flag logic
            if args.path and not self.viv.local_source:
                error("No local viv found to import from")

            if args.path and args.standalone:
                error("-p/--path and -s/--standalone are mutually exclusive")

        if name == "manage_install" and self.viv.local_source:
            error(
                f"found existing viv installation at {self.viv.local_source}",
                "use "
                + a.style("viv manage update", "bold")
                + " to modify current installation.",
            )

        if name == "manage_update":
            if not self.viv.local_source:
                error(
                    a.style("viv manage update", "bold")
                    + " should be used with an exisiting installation",
                )

            if self.viv.git:
                error(
                    a.style("viv manage update", "bold")
                    + " shouldn't be used with a git-based installation",
                )

        if name in ("run", "shim"):
            if not (args.reqs or args.script):
                error("must specify a requirement or --script")

        if name == "env_info":
            if args.use_json and args.path:
                error("--json and -p/--path are mutually exclusive")

    def _get_subcmd_parser(
        self,
        subparsers: _SubParsersAction[ArgumentParser],
        name: str,
        attr: Optional[str] = None,
        **kwargs: Any,
    ) -> ArgumentParser:
        aliases = kwargs.pop("aliases", [name[0]])

        cmd = getattr(self.viv, attr if attr else f"cmd_{name}")

        parser: ArgumentParser = subparsers.add_parser(
            name,
            help=cmd.__doc__.splitlines()[0],
            description=dedent(cmd.__doc__),
            aliases=aliases,
            **kwargs,
        )
        parser.set_defaults(func=cmd)

        return parser

    def run(self) -> None:
        self.parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"{a.bold}viv{a.end}, version {a.cyan}{__version__}{a.end}",
        )

        cmd_p = self.parser.add_subparsers(
            metavar="<sub-cmd>", title="subcommands", required=True
        )

        for cmd, subcmds in self.cmds.items():
            if subcmds:
                subcmd_p = self._get_subcmd_parser(cmd_p, cmd)
                subcmd_cmd_p = subcmd_p.add_subparsers(
                    title="subcommand",
                    metavar="<sub-cmd>",
                    required=True,
                )
                for subcmd, kwargs in subcmds.items():
                    subcmd_cmd_p.add_parser(
                        subcmd,
                        parents=[
                            self.parsers[k]
                            for k in self.cmd_arg_group_map[f"{cmd}_{subcmd}"]
                        ],
                        **kwargs,
                    ).set_defaults(func=getattr(self.viv, f"cmd_{cmd}_{subcmd}"))

            else:
                self._get_subcmd_parser(
                    cmd_p,
                    cmd,
                    parents=[self.parsers.get(k) for k in self.cmd_arg_group_map[cmd]],
                )
        if "--" in sys.argv:
            i = sys.argv.index("--")
            args = self.parser.parse_args(sys.argv[1:i])
            args.rest = sys.argv[i + 1 :]
        elif {"r", "run"} & set(sys.argv[1:2]) and (
            flag := list({"-s", "--script"} & set(sys.argv))
        ):
            i = sys.argv.index(flag[0])
            args = self.parser.parse_args(sys.argv[1 : i + 2])
            args.rest = sys.argv[i + 2 :]
        else:
            args = self.parser.parse_args()
            if args.func.__name__ in ("cmd_run", "cmd_env_exe"):
                args.rest = []

        self._validate_args(args)
        func = args.__dict__.pop("func")
        func(
            **vars(args),
        )


def _no_traceback_excepthook(exc_type, exc_val, traceback):
    # https://stackoverflow.com/questions/7073268/remove-traceback-in-python-on-ctrl-c
    pass


def main() -> None:
    try:
        viv = Viv()
        Cli(viv).run()
    except KeyboardInterrupt:
        echo(f"caught {a.bold}SIGINT")
        if sys.excepthook is sys.__excepthook__:
            sys.excepthook = _no_traceback_excepthook
        raise


if __name__ == "__main__":
    main()
