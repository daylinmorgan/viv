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
from enum import Enum
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

__version__ = "2024.1005"


#### START VENDORED TOMLI ####

if sys.version_info >= (3, 11):
    from tomllib import loads as toml_loads
else:
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

    v_tomli_ParseFloat = Callable[[str], Any]
    Key = Tuple[str, ...]
    v_tomli_Pos = int
    v_tomli__TIME_RE_STR = (
        "([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])(?:\\.([0-9]{1,6})[0-9]*)?"
    )
    v_tomli_RE_NUMBER = re.compile(
        """
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
        (?:\\.[0-9](?:_?[0-9])*)?         # optional fractional part
        (?:[eE][+-]?[0-9](?:_?[0-9])*)?  # optional exponent part
    )
    """,
        flags=re.VERBOSE,
    )
    v_tomli_RE_LOCALTIME = re.compile(v_tomli__TIME_RE_STR)
    v_tomli_RE_DATETIME = re.compile(
        f"""
    ([0-9]{{4}})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])  # date, e.g. 1988-10-27
    (?:
        [Tt ]
        {v_tomli__TIME_RE_STR}
        (?:([Zz])|([+-])([01][0-9]|2[0-3]):([0-5][0-9]))?  # optional time offset
    )?
    """,
        flags=re.VERBOSE,
    )

    def v_tomli_match_to_datetime(match: re.Match) -> datetime | date:
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
            tz: tzinfo | None = v_tomli_cached_tz(
                offset_hour_str, offset_minute_str, offset_sign_str
            )
        elif zulu_time:
            tz = timezone.utc
        else:
            tz = None
        return datetime(year, month, day, hour, minute, sec, micros, tzinfo=tz)

    @lru_cache(maxsize=None)
    def v_tomli_cached_tz(hour_str: str, minute_str: str, sign_str: str) -> timezone:
        sign = 1 if sign_str == "+" else -1
        return timezone(
            timedelta(hours=sign * int(hour_str), minutes=sign * int(minute_str))
        )

    def v_tomli_match_to_localtime(match: re.Match) -> time:
        hour_str, minute_str, sec_str, micros_str = match.groups()
        micros = int(micros_str.ljust(6, "0")) if micros_str else 0
        return time(int(hour_str), int(minute_str), int(sec_str), micros)

    def v_tomli_match_to_number(
        match: re.Match, parse_float: v_tomli_ParseFloat
    ) -> Any:
        if match.group("floatpart"):
            return parse_float(match.group())
        return int(match.group(), 0)

    v_tomli_ASCII_CTRL = frozenset(chr(i) for i in range(32)) | frozenset(chr(127))
    v_tomli_ILLEGAL_BASIC_STR_CHARS = v_tomli_ASCII_CTRL - frozenset("\t")
    v_tomli_ILLEGAL_MULTILINE_BASIC_STR_CHARS = v_tomli_ASCII_CTRL - frozenset("\t\n")
    v_tomli_ILLEGAL_LITERAL_STR_CHARS = v_tomli_ILLEGAL_BASIC_STR_CHARS
    v_tomli_ILLEGAL_MULTILINE_LITERAL_STR_CHARS = (
        v_tomli_ILLEGAL_MULTILINE_BASIC_STR_CHARS
    )
    v_tomli_ILLEGAL_COMMENT_CHARS = v_tomli_ILLEGAL_BASIC_STR_CHARS
    v_tomli_TOML_WS = frozenset(" \t")
    v_tomli_TOML_WS_AND_NEWLINE = v_tomli_TOML_WS | frozenset("\n")
    v_tomli_BARE_KEY_CHARS = frozenset(string.ascii_letters + string.digits + "-_")
    v_tomli_KEY_INITIAL_CHARS = v_tomli_BARE_KEY_CHARS | frozenset("\"'")
    v_tomli_HEXDIGIT_CHARS = frozenset(string.hexdigits)
    v_tomli_BASIC_STR_ESCAPE_REPLACEMENTS = MappingProxyType(
        {
            "\\b": "\x08",
            "\\t": "\t",
            "\\n": "\n",
            "\\f": "\x0c",
            "\\r": "\r",
            '\\"': '"',
            "\\\\": "\\",
        }
    )

    class v_tomli_TOMLDecodeError(ValueError):
        pass

    def v_tomli_load(
        __fp: IO[bytes], *, parse_float: v_tomli_ParseFloat = float
    ) -> dict[str, Any]:
        b = __fp.read()
        try:
            s = b.decode()
        except AttributeError:
            raise TypeError(
                "File must be opened in binary mode, e.g. use `open('foo.toml', 'rb')`"
            ) from None
        return v_tomli_loads(s, parse_float=parse_float)

    def v_tomli_loads(
        __s: str, *, parse_float: v_tomli_ParseFloat = float
    ) -> dict[str, Any]:
        src = __s.replace("\r\n", "\n")
        pos = 0
        out = v_tomli_Output(v_tomli_NestedDict(), v_tomli_Flags())
        header: Key = ()
        parse_float = v_tomli_make_safe_parse_float(parse_float)
        while True:
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
            try:
                char = src[pos]
            except IndexError:
                break
            if char == "\n":
                pos += 1
                continue
            if char in v_tomli_KEY_INITIAL_CHARS:
                pos = v_tomli_key_value_rule(src, pos, out, header, parse_float)
                pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
            elif char == "[":
                try:
                    second_char: str | None = src[pos + 1]
                except IndexError:
                    second_char = None
                out.flags.finalize_pending()
                if second_char == "[":
                    pos, header = v_tomli_create_list_rule(src, pos, out)
                else:
                    pos, header = v_tomli_create_dict_rule(src, pos, out)
                pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
            elif char != "#":
                raise v_tomli_suffixed_err(src, pos, "Invalid statement")
            pos = v_tomli_skip_comment(src, pos)
            try:
                char = src[pos]
            except IndexError:
                break
            if char != "\n":
                raise v_tomli_suffixed_err(
                    src, pos, "Expected newline or end of document after a statement"
                )
            pos += 1
        return out.data.dict

    class v_tomli_Flags:
        FROZEN = 0
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

        def set(self, key: Key, flag: int, *, recursive: bool) -> None:
            cont = self._flags
            key_parent, key_stem = key[:-1], key[-1]
            for k in key_parent:
                if k not in cont:
                    cont[k] = {"flags": set(), "recursive_flags": set(), "nested": {}}
                cont = cont[k]["nested"]
            if key_stem not in cont:
                cont[key_stem] = {
                    "flags": set(),
                    "recursive_flags": set(),
                    "nested": {},
                }
            cont[key_stem]["recursive_flags" if recursive else "flags"].add(flag)

        def is_(self, key: Key, flag: int) -> bool:
            if not key:
                return False
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

    class v_tomli_NestedDict:
        def __init__(self) -> None:
            self.dict: dict[str, Any] = {}

        def get_or_create_nest(self, key: Key, *, access_lists: bool = True) -> dict:
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

    class v_tomli_Output(NamedTuple):
        data: v_tomli_NestedDict
        flags: v_tomli_Flags

    def v_tomli_skip_chars(
        src: str, pos: v_tomli_Pos, chars: Iterable[str]
    ) -> v_tomli_Pos:
        try:
            while src[pos] in chars:
                pos += 1
        except IndexError:
            pass
        return pos

    def v_tomli_skip_until(
        src: str,
        pos: v_tomli_Pos,
        expect: str,
        *,
        error_on: frozenset[str],
        error_on_eof: bool,
    ) -> v_tomli_Pos:
        try:
            new_pos = src.index(expect, pos)
        except ValueError:
            new_pos = len(src)
            if error_on_eof:
                raise v_tomli_suffixed_err(
                    src, new_pos, f"Expected {expect!r}"
                ) from None
        if not error_on.isdisjoint(src[pos:new_pos]):
            while src[pos] not in error_on:
                pos += 1
            raise v_tomli_suffixed_err(
                src, pos, f"Found invalid character {src[pos]!r}"
            )
        return new_pos

    def v_tomli_skip_comment(src: str, pos: v_tomli_Pos) -> v_tomli_Pos:
        try:
            char: str | None = src[pos]
        except IndexError:
            char = None
        if char == "#":
            return v_tomli_skip_until(
                src,
                pos + 1,
                "\n",
                error_on=v_tomli_ILLEGAL_COMMENT_CHARS,
                error_on_eof=False,
            )
        return pos

    def v_tomli_skip_comments_and_array_ws(src: str, pos: v_tomli_Pos) -> v_tomli_Pos:
        while True:
            pos_before_skip = pos
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS_AND_NEWLINE)
            pos = v_tomli_skip_comment(src, pos)
            if pos == pos_before_skip:
                return pos

    def v_tomli_create_dict_rule(
        src: str, pos: v_tomli_Pos, out: v_tomli_Output
    ) -> tuple[v_tomli_Pos, Key]:
        pos += 1
        pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
        pos, key = v_tomli_parse_key(src, pos)
        if out.flags.is_(key, v_tomli_Flags.EXPLICIT_NEST) or out.flags.is_(
            key, v_tomli_Flags.FROZEN
        ):
            raise v_tomli_suffixed_err(src, pos, f"Cannot declare {key} twice")
        out.flags.set(key, v_tomli_Flags.EXPLICIT_NEST, recursive=False)
        try:
            out.data.get_or_create_nest(key)
        except KeyError:
            raise v_tomli_suffixed_err(src, pos, "Cannot overwrite a value") from None
        if not src.startswith("]", pos):
            raise v_tomli_suffixed_err(
                src, pos, "Expected ']' at the end of a table declaration"
            )
        return pos + 1, key

    def v_tomli_create_list_rule(
        src: str, pos: v_tomli_Pos, out: v_tomli_Output
    ) -> tuple[v_tomli_Pos, Key]:
        pos += 2
        pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
        pos, key = v_tomli_parse_key(src, pos)
        if out.flags.is_(key, v_tomli_Flags.FROZEN):
            raise v_tomli_suffixed_err(
                src, pos, f"Cannot mutate immutable namespace {key}"
            )
        out.flags.unset_all(key)
        out.flags.set(key, v_tomli_Flags.EXPLICIT_NEST, recursive=False)
        try:
            out.data.append_nest_to_list(key)
        except KeyError:
            raise v_tomli_suffixed_err(src, pos, "Cannot overwrite a value") from None
        if not src.startswith("]]", pos):
            raise v_tomli_suffixed_err(
                src, pos, "Expected ']]' at the end of an array declaration"
            )
        return pos + 2, key

    def v_tomli_key_value_rule(
        src: str,
        pos: v_tomli_Pos,
        out: v_tomli_Output,
        header: Key,
        parse_float: v_tomli_ParseFloat,
    ) -> v_tomli_Pos:
        pos, key, value = v_tomli_parse_key_value_pair(src, pos, parse_float)
        key_parent, key_stem = key[:-1], key[-1]
        abs_key_parent = header + key_parent
        relative_path_cont_keys = (header + key[:i] for i in range(1, len(key)))
        for cont_key in relative_path_cont_keys:
            if out.flags.is_(cont_key, v_tomli_Flags.EXPLICIT_NEST):
                raise v_tomli_suffixed_err(
                    src, pos, f"Cannot redefine namespace {cont_key}"
                )
            out.flags.add_pending(cont_key, v_tomli_Flags.EXPLICIT_NEST)
        if out.flags.is_(abs_key_parent, v_tomli_Flags.FROZEN):
            raise v_tomli_suffixed_err(
                src, pos, f"Cannot mutate immutable namespace {abs_key_parent}"
            )
        try:
            nest = out.data.get_or_create_nest(abs_key_parent)
        except KeyError:
            raise v_tomli_suffixed_err(src, pos, "Cannot overwrite a value") from None
        if key_stem in nest:
            raise v_tomli_suffixed_err(src, pos, "Cannot overwrite a value")
        if isinstance(value, (dict, list)):
            out.flags.set(header + key, v_tomli_Flags.FROZEN, recursive=True)
        nest[key_stem] = value
        return pos

    def v_tomli_parse_key_value_pair(
        src: str, pos: v_tomli_Pos, parse_float: v_tomli_ParseFloat
    ) -> tuple[v_tomli_Pos, Key, Any]:
        pos, key = v_tomli_parse_key(src, pos)
        try:
            char: str | None = src[pos]
        except IndexError:
            char = None
        if char != "=":
            raise v_tomli_suffixed_err(
                src, pos, "Expected '=' after a key in a key/value pair"
            )
        pos += 1
        pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
        pos, value = v_tomli_parse_value(src, pos, parse_float)
        return pos, key, value

    def v_tomli_parse_key(src: str, pos: v_tomli_Pos) -> tuple[v_tomli_Pos, Key]:
        pos, key_part = v_tomli_parse_key_part(src, pos)
        key: Key = (key_part,)
        pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
        while True:
            try:
                char: str | None = src[pos]
            except IndexError:
                char = None
            if char != ".":
                return pos, key
            pos += 1
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
            pos, key_part = v_tomli_parse_key_part(src, pos)
            key += (key_part,)
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)

    def v_tomli_parse_key_part(src: str, pos: v_tomli_Pos) -> tuple[v_tomli_Pos, str]:
        try:
            char: str | None = src[pos]
        except IndexError:
            char = None
        if char in v_tomli_BARE_KEY_CHARS:
            start_pos = pos
            pos = v_tomli_skip_chars(src, pos, v_tomli_BARE_KEY_CHARS)
            return pos, src[start_pos:pos]
        if char == "'":
            return v_tomli_parse_literal_str(src, pos)
        if char == '"':
            return v_tomli_parse_one_line_basic_str(src, pos)
        raise v_tomli_suffixed_err(src, pos, "Invalid initial character for a key part")

    def v_tomli_parse_one_line_basic_str(
        src: str, pos: v_tomli_Pos
    ) -> tuple[v_tomli_Pos, str]:
        pos += 1
        return v_tomli_parse_basic_str(src, pos, multiline=False)

    def v_tomli_parse_array(
        src: str, pos: v_tomli_Pos, parse_float: v_tomli_ParseFloat
    ) -> tuple[v_tomli_Pos, list]:
        pos += 1
        array: list = []
        pos = v_tomli_skip_comments_and_array_ws(src, pos)
        if src.startswith("]", pos):
            return pos + 1, array
        while True:
            pos, val = v_tomli_parse_value(src, pos, parse_float)
            array.append(val)
            pos = v_tomli_skip_comments_and_array_ws(src, pos)
            c = src[pos : pos + 1]
            if c == "]":
                return pos + 1, array
            if c != ",":
                raise v_tomli_suffixed_err(src, pos, "Unclosed array")
            pos += 1
            pos = v_tomli_skip_comments_and_array_ws(src, pos)
            if src.startswith("]", pos):
                return pos + 1, array

    def v_tomli_parse_inline_table(
        src: str, pos: v_tomli_Pos, parse_float: v_tomli_ParseFloat
    ) -> tuple[v_tomli_Pos, dict]:
        pos += 1
        nested_dict = v_tomli_NestedDict()
        flags = v_tomli_Flags()
        pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
        if src.startswith("}", pos):
            return pos + 1, nested_dict.dict
        while True:
            pos, key, value = v_tomli_parse_key_value_pair(src, pos, parse_float)
            key_parent, key_stem = key[:-1], key[-1]
            if flags.is_(key, v_tomli_Flags.FROZEN):
                raise v_tomli_suffixed_err(
                    src, pos, f"Cannot mutate immutable namespace {key}"
                )
            try:
                nest = nested_dict.get_or_create_nest(key_parent, access_lists=False)
            except KeyError:
                raise v_tomli_suffixed_err(
                    src, pos, "Cannot overwrite a value"
                ) from None
            if key_stem in nest:
                raise v_tomli_suffixed_err(
                    src, pos, f"Duplicate inline table key {key_stem!r}"
                )
            nest[key_stem] = value
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
            c = src[pos : pos + 1]
            if c == "}":
                return pos + 1, nested_dict.dict
            if c != ",":
                raise v_tomli_suffixed_err(src, pos, "Unclosed inline table")
            if isinstance(value, (dict, list)):
                flags.set(key, v_tomli_Flags.FROZEN, recursive=True)
            pos += 1
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)

    def v_tomli_parse_basic_str_escape(
        src: str, pos: v_tomli_Pos, *, multiline: bool = False
    ) -> tuple[v_tomli_Pos, str]:
        escape_id = src[pos : pos + 2]
        pos += 2
        if multiline and escape_id in {"\\ ", "\\\t", "\\\n"}:
            if escape_id != "\\\n":
                pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS)
                try:
                    char = src[pos]
                except IndexError:
                    return pos, ""
                if char != "\n":
                    raise v_tomli_suffixed_err(src, pos, "Unescaped '\\' in a string")
                pos += 1
            pos = v_tomli_skip_chars(src, pos, v_tomli_TOML_WS_AND_NEWLINE)
            return pos, ""
        if escape_id == "\\u":
            return v_tomli_parse_hex_char(src, pos, 4)
        if escape_id == "\\U":
            return v_tomli_parse_hex_char(src, pos, 8)
        try:
            return pos, v_tomli_BASIC_STR_ESCAPE_REPLACEMENTS[escape_id]
        except KeyError:
            raise v_tomli_suffixed_err(src, pos, "Unescaped '\\' in a string") from None

    def v_tomli_parse_basic_str_escape_multiline(
        src: str, pos: v_tomli_Pos
    ) -> tuple[v_tomli_Pos, str]:
        return v_tomli_parse_basic_str_escape(src, pos, multiline=True)

    def v_tomli_parse_hex_char(
        src: str, pos: v_tomli_Pos, hex_len: int
    ) -> tuple[v_tomli_Pos, str]:
        hex_str = src[pos : pos + hex_len]
        if len(hex_str) != hex_len or not v_tomli_HEXDIGIT_CHARS.issuperset(hex_str):
            raise v_tomli_suffixed_err(src, pos, "Invalid hex value")
        pos += hex_len
        hex_int = int(hex_str, 16)
        if not v_tomli_is_unicode_scalar_value(hex_int):
            raise v_tomli_suffixed_err(
                src, pos, "Escaped character is not a Unicode scalar value"
            )
        return pos, chr(hex_int)

    def v_tomli_parse_literal_str(
        src: str, pos: v_tomli_Pos
    ) -> tuple[v_tomli_Pos, str]:
        pos += 1
        start_pos = pos
        pos = v_tomli_skip_until(
            src, pos, "'", error_on=v_tomli_ILLEGAL_LITERAL_STR_CHARS, error_on_eof=True
        )
        return pos + 1, src[start_pos:pos]

    def v_tomli_parse_multiline_str(
        src: str, pos: v_tomli_Pos, *, literal: bool
    ) -> tuple[v_tomli_Pos, str]:
        pos += 3
        if src.startswith("\n", pos):
            pos += 1
        if literal:
            delim = "'"
            end_pos = v_tomli_skip_until(
                src,
                pos,
                "'''",
                error_on=v_tomli_ILLEGAL_MULTILINE_LITERAL_STR_CHARS,
                error_on_eof=True,
            )
            result = src[pos:end_pos]
            pos = end_pos + 3
        else:
            delim = '"'
            pos, result = v_tomli_parse_basic_str(src, pos, multiline=True)
        if not src.startswith(delim, pos):
            return pos, result
        pos += 1
        if not src.startswith(delim, pos):
            return pos, result + delim
        pos += 1
        return pos, result + delim * 2

    def v_tomli_parse_basic_str(
        src: str, pos: v_tomli_Pos, *, multiline: bool
    ) -> tuple[v_tomli_Pos, str]:
        if multiline:
            error_on = v_tomli_ILLEGAL_MULTILINE_BASIC_STR_CHARS
            parse_escapes = v_tomli_parse_basic_str_escape_multiline
        else:
            error_on = v_tomli_ILLEGAL_BASIC_STR_CHARS
            parse_escapes = v_tomli_parse_basic_str_escape
        result = ""
        start_pos = pos
        while True:
            try:
                char = src[pos]
            except IndexError:
                raise v_tomli_suffixed_err(src, pos, "Unterminated string") from None
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
                raise v_tomli_suffixed_err(src, pos, f"Illegal character {char!r}")
            pos += 1

    def v_tomli_parse_value(
        src: str, pos: v_tomli_Pos, parse_float: v_tomli_ParseFloat
    ) -> tuple[v_tomli_Pos, Any]:
        try:
            char: str | None = src[pos]
        except IndexError:
            char = None
        if char == '"':
            if src.startswith('"""', pos):
                return v_tomli_parse_multiline_str(src, pos, literal=False)
            return v_tomli_parse_one_line_basic_str(src, pos)
        if char == "'":
            if src.startswith("'''", pos):
                return v_tomli_parse_multiline_str(src, pos, literal=True)
            return v_tomli_parse_literal_str(src, pos)
        if char == "t":
            if src.startswith("true", pos):
                return pos + 4, True
        if char == "f":
            if src.startswith("false", pos):
                return pos + 5, False
        if char == "[":
            return v_tomli_parse_array(src, pos, parse_float)
        if char == "{":
            return v_tomli_parse_inline_table(src, pos, parse_float)
        datetime_match = v_tomli_RE_DATETIME.match(src, pos)
        if datetime_match:
            try:
                datetime_obj = v_tomli_match_to_datetime(datetime_match)
            except ValueError as e:
                raise v_tomli_suffixed_err(src, pos, "Invalid date or datetime") from e
            return datetime_match.end(), datetime_obj
        localtime_match = v_tomli_RE_LOCALTIME.match(src, pos)
        if localtime_match:
            return localtime_match.end(), v_tomli_match_to_localtime(localtime_match)
        number_match = v_tomli_RE_NUMBER.match(src, pos)
        if number_match:
            return number_match.end(), v_tomli_match_to_number(
                number_match, parse_float
            )
        first_three = src[pos : pos + 3]
        if first_three in {"inf", "nan"}:
            return pos + 3, parse_float(first_three)
        first_four = src[pos : pos + 4]
        if first_four in {"-inf", "+inf", "-nan", "+nan"}:
            return pos + 4, parse_float(first_four)
        raise v_tomli_suffixed_err(src, pos, "Invalid value")

    def v_tomli_suffixed_err(
        src: str, pos: v_tomli_Pos, msg: str
    ) -> v_tomli_TOMLDecodeError:
        def coord_repr(src: str, pos: v_tomli_Pos) -> str:
            if pos >= len(src):
                return "end of document"
            line = src.count("\n", 0, pos) + 1
            if line == 1:
                column = pos + 1
            else:
                column = pos - src.rindex("\n", 0, pos)
            return f"line {line}, column {column}"

        return v_tomli_TOMLDecodeError(f"{msg} (at {coord_repr(src, pos)})")

    def v_tomli_is_unicode_scalar_value(codepoint: int) -> bool:
        return 0 <= codepoint <= 55295 or 57344 <= codepoint <= 1114111

    def v_tomli_make_safe_parse_float(
        parse_float: v_tomli_ParseFloat,
    ) -> v_tomli_ParseFloat:
        if parse_float is float:
            return float

        def safe_parse_float(float_str: str) -> Any:
            float_value = parse_float(float_str)
            if isinstance(float_value, (dict, list)):
                raise ValueError("parse_float must not return dicts or lists")
            return float_value

        return safe_parse_float

    toml_loads = v_tomli_loads

#### END VENDORED TOMLI ####


#### START VENDORED PACKAGING ####

# MODIFIED FROM https://github.com/pypa/packaging
# see repo for original licenses
# This software is made available under the terms of *either* of the licenses
# found in LICENSE.APACHE or LICENSE.BSD. Contributions to this software is made
# under the terms of *both* these licenses.

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


class v_packaging_InfinityType:
    def __repr__(self) -> str:
        return "v_packaging_Infinity"

    def __hash__(self) -> int:
        return hash(repr(self))

    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__)

    def __gt__(self, other: object) -> bool:
        return True

    def __ge__(self, other: object) -> bool:
        return True

    def __neg__(self: object) -> "v_packaging_NegativeInfinityType":
        return v_packaging_NegativeInfinity


v_packaging_Infinity = v_packaging_InfinityType()


class v_packaging_NegativeInfinityType:
    def __repr__(self) -> str:
        return "-Infinity"

    def __hash__(self) -> int:
        return hash(repr(self))

    def __lt__(self, other: object) -> bool:
        return True

    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__)

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return False

    def __neg__(self: object) -> v_packaging_InfinityType:
        return v_packaging_Infinity


v_packaging_NegativeInfinity = v_packaging_NegativeInfinityType()
v_packaging_LocalType = Tuple[Union[int, str], ...]
v_packaging_CmpPrePostDevType = Union[
    v_packaging_InfinityType, v_packaging_NegativeInfinityType, Tuple[str, int]
]
v_packaging_CmpLocalType = Union[
    v_packaging_NegativeInfinityType,
    Tuple[
        Union[
            Tuple[int, str], Tuple[v_packaging_NegativeInfinityType, Union[int, str]]
        ],
        ...,
    ],
]
v_packaging_CmpKey = Tuple[
    int,
    Tuple[int, ...],
    v_packaging_CmpPrePostDevType,
    v_packaging_CmpPrePostDevType,
    v_packaging_CmpPrePostDevType,
    v_packaging_CmpLocalType,
]
v_packaging_VersionComparisonMethod = Callable[
    [v_packaging_CmpKey, v_packaging_CmpKey], bool
]


class v_packaging__Version(NamedTuple):
    epoch: int
    release: Tuple[int, ...]
    dev: Optional[Tuple[str, int]]
    pre: Optional[Tuple[str, int]]
    post: Optional[Tuple[str, int]]
    local: Optional[v_packaging_LocalType]


def v_packaging_parse(version: str) -> "v_packaging_Version":
    return v_packaging_Version(version)


class v_packaging_InvalidVersion(ValueError):
    pass


class v_packaging__BaseVersion:
    _key: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    def __lt__(self, other: "v_packaging__BaseVersion") -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key < other._key

    def __le__(self, other: "v_packaging__BaseVersion") -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key == other._key

    def __ge__(self, other: "v_packaging__BaseVersion") -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key >= other._key

    def __gt__(self, other: "v_packaging__BaseVersion") -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, v_packaging__BaseVersion):
            return NotImplemented
        return self._key != other._key


v_packaging__VERSION_PATTERN = """
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\\.]?
                (?P<post_l>post|rev|r)
                [-_\\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\\.]?
            (?P<dev_l>dev)
            [-_\\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\\+(?P<local>[a-z0-9]+(?:[-_\\.][a-z0-9]+)*))?       # local version
"""
v_packaging_VERSION_PATTERN = v_packaging__VERSION_PATTERN


class v_packaging_Version(v_packaging__BaseVersion):
    _regex = re.compile(
        "^\\s*" + v_packaging_VERSION_PATTERN + "\\s*$", re.VERBOSE | re.IGNORECASE
    )
    _key: v_packaging_CmpKey

    def __init__(self, version: str) -> None:
        match = self._regex.search(version)
        if not match:
            raise v_packaging_InvalidVersion(f"Invalid version: '{version}'")
        self._version = v_packaging__Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=v_packaging__parse_letter_version(
                match.group("pre_l"), match.group("pre_n")
            ),
            post=v_packaging__parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=v_packaging__parse_letter_version(
                match.group("dev_l"), match.group("dev_n")
            ),
            local=v_packaging__parse_local_version(match.group("local")),
        )
        self._key = v_packaging__cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        parts = []
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")
        parts.append(".".join(str(x) for x in self.release))
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))
        if self.post is not None:
            parts.append(f".post{self.post}")
        if self.dev is not None:
            parts.append(f".dev{self.dev}")
        if self.local is not None:
            parts.append(f"+{self.local}")
        return "".join(parts)

    @property
    def epoch(self) -> int:
        return self._version.epoch

    @property
    def release(self) -> Tuple[int, ...]:
        return self._version.release

    @property
    def pre(self) -> Optional[Tuple[str, int]]:
        return self._version.pre

    @property
    def post(self) -> Optional[int]:
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> Optional[int]:
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> Optional[str]:
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        parts = []
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")
        parts.append(".".join(str(x) for x in self.release))
        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        return self.dev is not None

    @property
    def major(self) -> int:
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        return self.release[2] if len(self.release) >= 3 else 0


def v_packaging__parse_letter_version(
    letter: Optional[str], number: Union[str, bytes, SupportsInt, None]
) -> Optional[Tuple[str, int]]:
    if letter:
        if number is None:
            number = 0
        letter = letter.lower()
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"
        return letter, int(number)
    if not letter and number:
        letter = "post"
        return letter, int(number)
    return None


v_packaging__local_version_separators = re.compile("[\\._-]")


def v_packaging__parse_local_version(
    local: Optional[str],
) -> Optional[v_packaging_LocalType]:
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in v_packaging__local_version_separators.split(local)
        )
    return None


def v_packaging__cmpkey(
    epoch: int,
    release: Tuple[int, ...],
    pre: Optional[Tuple[str, int]],
    post: Optional[Tuple[str, int]],
    dev: Optional[Tuple[str, int]],
    local: Optional[v_packaging_LocalType],
) -> v_packaging_CmpKey:
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )
    if pre is None and post is None and dev is not None:
        _pre: v_packaging_CmpPrePostDevType = v_packaging_NegativeInfinity
    elif pre is None:
        _pre = v_packaging_Infinity
    else:
        _pre = pre
    if post is None:
        _post: v_packaging_CmpPrePostDevType = v_packaging_NegativeInfinity
    else:
        _post = post
    if dev is None:
        _dev: v_packaging_CmpPrePostDevType = v_packaging_Infinity
    else:
        _dev = dev
    if local is None:
        _local: v_packaging_CmpLocalType = v_packaging_NegativeInfinity
    else:
        _local = tuple(
            (i, "") if isinstance(i, int) else (v_packaging_NegativeInfinity, i)
            for i in local
        )
    return epoch, _release, _pre, _post, _dev, _local


def v_packaging_canonicalize_version(
    version: Union[v_packaging_Version, str], *, strip_trailing_zero: bool = True
) -> str:
    if isinstance(version, str):
        try:
            v_packaging_parsed = v_packaging_Version(version)
        except v_packaging_InvalidVersion:
            return version
    else:
        v_packaging_parsed = version
    parts = []
    if v_packaging_parsed.epoch != 0:
        parts.append(f"{v_packaging_parsed.epoch}!")
    release_segment = ".".join(str(x) for x in v_packaging_parsed.release)
    if strip_trailing_zero:
        release_segment = re.sub("(\\.0)+$", "", release_segment)
    parts.append(release_segment)
    if v_packaging_parsed.pre is not None:
        parts.append("".join(str(x) for x in v_packaging_parsed.pre))
    if v_packaging_parsed.post is not None:
        parts.append(f".post{v_packaging_parsed.post}")
    if v_packaging_parsed.dev is not None:
        parts.append(f".dev{v_packaging_parsed.dev}")
    if v_packaging_parsed.local is not None:
        parts.append(f"+{v_packaging_parsed.local}")
    return "".join(parts)


v_packaging_UnparsedVersion = Union[v_packaging_Version, str]
v_packaging_UnparsedVersionVar = TypeVar(
    "v_packaging_UnparsedVersionVar", bound=v_packaging_UnparsedVersion
)
v_packaging_CallableOperator = Callable[[v_packaging_Version, str], bool]


def v_packaging__coerce_version(
    version: v_packaging_UnparsedVersion,
) -> v_packaging_Version:
    if not isinstance(version, v_packaging_Version):
        version = v_packaging_Version(version)
    return version


class v_packaging_InvalidSpecifier(ValueError):
    pass


class v_packaging_BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        pass

    @abc.abstractmethod
    def __hash__(self) -> int:
        pass

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        pass

    @property
    @abc.abstractmethod
    def prereleases(self) -> Optional[bool]:
        pass

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        pass

    @abc.abstractmethod
    def contains(self, item: str, prereleases: Optional[bool] = None) -> bool:
        pass

    @abc.abstractmethod
    def filter(
        self,
        iterable: Iterable[v_packaging_UnparsedVersionVar],
        prereleases: Optional[bool] = None,
    ) -> Iterator[v_packaging_UnparsedVersionVar]:
        pass


class v_packaging_Specifier(v_packaging_BaseSpecifier):
    _operator_regex_str = """
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = """
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be v_packaging_parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \\s*
                [^\\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals
                \\s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\\.[0-9]+)*   # release
                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \\.\\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\\.]?(post|rev|r)[-_\\.]?[0-9]*)
                    )?
                    (?:[-_\\.]?dev[-_\\.]?[0-9]*)?         # dev release
                    (?:\\+[a-z0-9]+(?:[-_\\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator
                \\s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\\.]?(post|rev|r)[-_\\.]?[0-9]*)
                )?
                (?:[-_\\.]?dev[-_\\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.
                \\s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\\.]?(post|rev|r)[-_\\.]?[0-9]*)
                )?
                (?:[-_\\.]?dev[-_\\.]?[0-9]*)?          # dev release
            )
        )
        """
    _regex = re.compile(
        "^\\s*" + _operator_regex_str + _version_regex_str + "\\s*$",
        re.VERBOSE | re.IGNORECASE,
    )
    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: Optional[bool] = None) -> None:
        match = self._regex.search(spec)
        if not match:
            raise v_packaging_InvalidSpecifier(f"Invalid specifier: '{spec}'")
        self._spec: Tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )
        self._prereleases = prereleases

    @property
    def prereleases(self) -> bool:
        if self._prereleases is not None:
            return self._prereleases
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "==="]:
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]
            if v_packaging_Version(version).is_prerelease:
                return True
        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        return self._spec[0]

    @property
    def version(self) -> str:
        return self._spec[1]

    def __repr__(self) -> str:
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )
        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> Tuple[str, str]:
        canonical_version = v_packaging_canonicalize_version(
            self._spec[1], strip_trailing_zero=self._spec[0] != "~="
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except v_packaging_InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented
        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> v_packaging_CallableOperator:
        operator_callable: v_packaging_CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: v_packaging_Version, spec: str) -> bool:
        prefix = v_packaging__version_join(
            list(
                itertools.takewhile(
                    v_packaging__is_not_suffix, v_packaging__version_split(spec)
                )
            )[:-1]
        )
        prefix += ".*"
        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: v_packaging_Version, spec: str) -> bool:
        if spec.endswith(".*"):
            normalized_prospective = v_packaging_canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            normalized_spec = v_packaging_canonicalize_version(
                spec[:-2], strip_trailing_zero=False
            )
            split_spec = v_packaging__version_split(normalized_spec)
            split_prospective = v_packaging__version_split(normalized_prospective)
            padded_prospective, _ = v_packaging__pad_version(
                split_prospective, split_spec
            )
            shortened_prospective = padded_prospective[: len(split_spec)]
            return shortened_prospective == split_spec
        else:
            spec_version = v_packaging_Version(spec)
            if not spec_version.local:
                prospective = v_packaging_Version(prospective.public)
            return prospective == spec_version

    def _compare_not_equal(self, prospective: v_packaging_Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(
        self, prospective: v_packaging_Version, spec: str
    ) -> bool:
        return v_packaging_Version(prospective.public) <= v_packaging_Version(spec)

    def _compare_greater_than_equal(
        self, prospective: v_packaging_Version, spec: str
    ) -> bool:
        return v_packaging_Version(prospective.public) >= v_packaging_Version(spec)

    def _compare_less_than(
        self, prospective: v_packaging_Version, spec_str: str
    ) -> bool:
        spec = v_packaging_Version(spec_str)
        if not prospective < spec:
            return False
        if not spec.is_prerelease and prospective.is_prerelease:
            if v_packaging_Version(prospective.base_version) == v_packaging_Version(
                spec.base_version
            ):
                return False
        return True

    def _compare_greater_than(
        self, prospective: v_packaging_Version, spec_str: str
    ) -> bool:
        spec = v_packaging_Version(spec_str)
        if not prospective > spec:
            return False
        if not spec.is_postrelease and prospective.is_postrelease:
            if v_packaging_Version(prospective.base_version) == v_packaging_Version(
                spec.base_version
            ):
                return False
        if prospective.local is not None:
            if v_packaging_Version(prospective.base_version) == v_packaging_Version(
                spec.base_version
            ):
                return False
        return True

    def _compare_arbitrary(self, prospective: v_packaging_Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: Union[str, v_packaging_Version]) -> bool:
        return self.contains(item)

    def contains(
        self, item: v_packaging_UnparsedVersion, prereleases: Optional[bool] = None
    ) -> bool:
        if prereleases is None:
            prereleases = self.prereleases
        normalized_item = v_packaging__coerce_version(item)
        if normalized_item.is_prerelease and not prereleases:
            return False
        operator_callable: v_packaging_CallableOperator = self._get_operator(
            self.operator
        )
        return operator_callable(normalized_item, self.version)

    def filter(
        self,
        iterable: Iterable[v_packaging_UnparsedVersionVar],
        prereleases: Optional[bool] = None,
    ) -> Iterator[v_packaging_UnparsedVersionVar]:
        yielded = False
        found_prereleases = []
        kw = {"prereleases": prereleases if prereleases is not None else True}
        for version in iterable:
            v_packaging_parsed_version = v_packaging__coerce_version(version)
            if self.contains(v_packaging_parsed_version, **kw):
                if v_packaging_parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                else:
                    yielded = True
                    yield version
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


v_packaging__prefix_regex = re.compile("^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def v_packaging__version_split(version: str) -> List[str]:
    result: List[str] = []
    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")
    for item in rest.split("."):
        match = v_packaging__prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def v_packaging__version_join(components: List[str]) -> str:
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def v_packaging__is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def v_packaging__pad_version(
    left: List[str], right: List[str]
) -> Tuple[List[str], List[str]]:
    left_split, right_split = [], []
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))
    return list(itertools.chain.from_iterable(left_split)), list(
        itertools.chain.from_iterable(right_split)
    )


class v_packaging_SpecifierSet(v_packaging_BaseSpecifier):
    def __init__(
        self, specifiers: str = "", prereleases: Optional[bool] = None
    ) -> None:
        split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]
        self._specs = frozenset(map(v_packaging_Specifier, split_specifiers))
        self._prereleases = prereleases

    @property
    def prereleases(self) -> Optional[bool]:
        if self._prereleases is not None:
            return self._prereleases
        if not self._specs:
            return None
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )
        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(
        self, other: Union["v_packaging_SpecifierSet", str]
    ) -> "v_packaging_SpecifierSet":
        if isinstance(other, str):
            other = v_packaging_SpecifierSet(other)
        elif not isinstance(other, v_packaging_SpecifierSet):
            return NotImplemented
        specifier = v_packaging_SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)
        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine v_packaging_SpecifierSets"
                "with True and False prerelease overrides."
            )
        return specifier

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (str, v_packaging_Specifier)):
            other = v_packaging_SpecifierSet(str(other))
        elif not isinstance(other, v_packaging_SpecifierSet):
            return NotImplemented
        return self._specs == other._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[v_packaging_Specifier]:
        return iter(self._specs)

    def __contains__(self, item: v_packaging_UnparsedVersion) -> bool:
        return self.contains(item)

    def contains(
        self,
        item: v_packaging_UnparsedVersion,
        prereleases: Optional[bool] = None,
        installed: Optional[bool] = None,
    ) -> bool:
        if not isinstance(item, v_packaging_Version):
            item = v_packaging_Version(item)
        if prereleases is None:
            prereleases = self.prereleases
        if not prereleases and item.is_prerelease:
            return False
        if installed and item.is_prerelease:
            item = v_packaging_Version(item.base_version)
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self,
        iterable: Iterable[v_packaging_UnparsedVersionVar],
        prereleases: Optional[bool] = None,
    ) -> Iterator[v_packaging_UnparsedVersionVar]:
        if prereleases is None:
            prereleases = self.prereleases
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        else:
            filtered: List[v_packaging_UnparsedVersionVar] = []
            found_prereleases: List[v_packaging_UnparsedVersionVar] = []
            for item in iterable:
                v_packaging_parsed_version = v_packaging__coerce_version(item)
                if v_packaging_parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)
            return iter(filtered)


Version = v_packaging_Version
SpecifierSet = v_packaging_SpecifierSet

#### END VENDORED PACKAGING ####


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
        self.is_win = platform.system() == "Windows"
        (self.bin_dir, *_) = ("Scripts",) if self.is_win else ("bin",)

    def bin(self, exe: str) -> str:
        return f"{exe}.exe" if self.is_win else exe


system = System()


class Cfg:
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
                symlinks=not system.is_win,
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

        unit = ""
        for unit in ("", "K", "M", "G", "T"):
            if size < 1024:
                break
            size /= 1024

        self.size = f"{size:.1f}{unit}B"

    @contextmanager
    def use(self, keep: bool = True, tmpdir: str = "") -> Generator[None, None, None]:
        run_mode = Env().viv_run_mode
        _path = self.path

        if tmpdir and not keep:
            _update_cache(run_mode=run_mode, tmpdir=tmpdir)

        try:
            self.set_path(Cfg().cache_venv / self.name)
            self.ensure()
            self.touch()
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


def run() -> Path:
    """create a vivenv and append to sys.path using embedded metadata"""
    source = get_caller_path().read_text()
    metadata = _read_metadata_block(source)
    deps = metadata.get("dependencies", [])
    if requires := metadata.get("requires-python", ""):
        _check_python(requires)
    return use(*deps)


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


class _Viv_Mode(Enum):
    NONE = 0
    USE = 1
    RUN = 2


def _uses_viv(txt: str) -> _Viv_Mode:
    matches = [
        match.group("mode")
        for match in re.finditer(
            r"""
            ^(?!\#)\s*    # ignore comments/shebangs
            (
              (?:__import__\(\s*["']viv["']\s*\)\.)
              |
              (?:from\s+viv\s+import\s+)
              |
              (?:viv\.)
            )
            (?P<mode>(\w+))
            """,
            txt,
            re.VERBOSE | re.MULTILINE,
        )
    ]
    if len(matches) == 0:
        return _Viv_Mode.NONE
    elif len(matches) > 1:
        err_quit(
            "Unexpected number of viv references in script.\n"
            "Expected only 1, found: "
            + ", ".join((a.style(match, "bold") for match in matches))
        )
    elif (match := matches[0]) in {"run", "use"}:
        return _Viv_Mode[match.upper()]
    else:
        err_quit(f"Unknown function {a.bold}{matches[0]}{a.end} associated with viv.")


METADATA_BLOCK = (
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
)


def _read_metadata_block(script: str) -> dict:
    name = "script"
    matches = list(
        filter(lambda m: m.group("type") == name, re.finditer(METADATA_BLOCK, script))
    )
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        return toml_loads(
            "\n".join((line[2:] for line in matches[0].group(0).splitlines()[1:-1]))
        )
    else:
        return {}


def _check_python(requires: str) -> None:
    version = Version(platform.python_version())
    if version not in SpecifierSet(requires):
        err_quit(
            f"Running python {a.yellow}{version}{a.end} does "
            f"not satisfy 'requires-python: {requires}'"
        )


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


def _update_cache(run_mode: str, tmpdir: str) -> None:
    new_cache = tmpdir

    if run_mode == "semi-ephemeral":
        new_cache = str(
            Path(tempfile.gettempdir()) / ("viv-ephemeral-cache-" + _get_user())
        )

    # by default ephemeral
    os.environ["VIV_CACHE"] = new_cache


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


class Script:
    def __init__(
        self, path: str, spec: List[str], keep: bool, rest: List[str], viv: Viv
    ):
        self.path = path
        self.spec = spec
        self.keep = keep
        self.rest = rest
        self.viv = viv

        self.name = path.split("/")[-1]
        self.remote = Path(path).is_file()  # does this work for symlinks?

    def run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viv-") as tmpdir:
            tmppath = Path(tmpdir)

            if self.remote:
                scriptpath = Path(self.path).absolute()
                script_text = scriptpath.read_text()
            else:
                scriptpath = tmppath / self.name
                script_text = fetch_script(self.path)
                scriptpath.write_text(script_text)

            mode = _uses_viv(script_text)
            metadata = _read_metadata_block(script_text)
            deps = metadata.get("dependencies", [])

            if requires := metadata.get("requires-python", ""):
                _check_python(requires)

            if mode == _Viv_Mode.USE and deps:
                error(
                    "Inline Script Metadata block and "
                    "`viv.use` API can't be used in the same script"
                )

            if not self.viv.local_source and mode != _Viv_Mode.NONE:
                log.debug("fetching remote copy to use for python api")
                (tmppath / "viv.py").write_text(
                    fetch_script(
                        "https://raw.githubusercontent.com/daylinmorgan/viv/latest/src/viv/viv.py"
                    )
                )

            _update_cache(run_mode=Env().viv_run_mode, tmpdir=tmpdir)

            env = dict(
                env := os.environ,
                PYTHONPATH=":".join((str(tmppath), env.get("PYTHONPATH", ""))),
            )

            if not self.spec and not deps:
                log.warning("using viv with empty spec, skipping vivenv creation")
                subprocess_run_quit([sys.executable, "-S", scriptpath, *self.rest])

            elif mode == _Viv_Mode.USE:
                log.debug(
                    f"script invokes viv.use passing along spec: \n  '{self.spec}'"
                )
                env.update(VIV_SPEC=" ".join(f"'{req}'" for req in self.spec))
                subprocess_run_quit(
                    [sys.executable, "-S", scriptpath, *self.rest], env=env
                )
            elif mode == _Viv_Mode.RUN:
                log.debug("script invokes viv.run letting subprocess handle deps")
                subprocess_run_quit(
                    [sys.executable, "-S", scriptpath, *self.rest], env=env
                )

            else:
                vivenv = ViVenv(self.spec + deps)
                with vivenv.use(keep=self.keep):
                    vivenv.meta.write()
                    subprocess_run_quit(
                        [vivenv.python, "-S", scriptpath, *self.rest],
                        env=dict(
                            env,
                            PYTHONPATH=":".join(
                                filter(None, (vivenv.site_packages, Env().pythonpath))
                            ),
                        ),
                    )


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
                        "PYTHONPATH": os.getenv("PYTHONPATH", ""),
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

    def _pick_bin(self, reqs: List[str], bin: str) -> str:
        default = system.bin(re.split(r"[=><~!*]+", reqs[0])[0])
        return default if not bin else bin

    def cmd_shim(
        self,
        reqs: List[str],
        requirements: Path,
        bin: str,
        output: Path,
        freeze: bool,
        generate: bool,
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

        bin = self._pick_bin(reqs, bin)
        output = Env().viv_bin_dir / bin if not output else output.absolute()

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
            if generate:
                vivenv = ViVenv(spec)
                with vivenv.use():
                    vivenv.meta.addfile(output)
                    vivenv.meta.write()

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
            Script(path=script, spec=spec, keep=keep, rest=rest, viv=self).run()
        else:
            bin = self._pick_bin(reqs, bin)
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
            BoolArg(flag="generate", help="create vivenv w/shim"),
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


def _pip_check():
    pip_version_requirement = ">=22.2"
    if not shutil.which("pip"):
        err_quit("viv requires pip to be installed")

    # importing viv may have side effects I'm not aware of...
    if Version((pip_version := __import__("pip").__version__)) not in SpecifierSet(
        pip_version_requirement
    ):
        err_quit(
            f"viv requires pip version {pip_version_requirement} but got {pip_version}"
        )


def _no_traceback_excepthook(
    exc_type: type[BaseException],
    exc_val: BaseException,
    traceback: TracebackType | None,
) -> None:
    # https://stackoverflow.com/questions/7073268/remove-traceback-in-python-on-ctrl-c
    pass


def main() -> None:
    try:
        _pip_check()
        viv = Viv()
        Cli(viv).run()
    except KeyboardInterrupt:
        echo(f"caught {a.bold}SIGINT")
        if sys.excepthook is sys.__excepthook__:
            sys.excepthook = _no_traceback_excepthook
        raise


if __name__ == "__main__":
    main()
