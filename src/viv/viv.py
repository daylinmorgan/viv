#!/usr/bin/env python3
"""Viv isn't venv!

  viv -h
    OR
  __import__("viv").activate("requests", "bs4")
"""

import hashlib
import itertools
import json
import os
import re
import shlex
import shutil
import site
import subprocess
import sys
import tempfile
import threading
import time
import venv
from argparse import SUPPRESS
from argparse import ArgumentParser as StdArgParser
from argparse import HelpFormatter, RawDescriptionHelpFormatter
from dataclasses import dataclass
from datetime import datetime
from itertools import zip_longest
from pathlib import Path
from textwrap import dedent, wrap
from typing import Dict, List, Tuple

__version__ = "22.12a3"


@dataclass
class Config:
    """viv config manager"""

    venvcache: Path = (
        Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".local" / "cache"))
        / "viv"
        / "venvs"
    )

    def __post_init__(self):
        self.venvcache.mkdir(parents=True, exist_ok=True)


c = Config()


class Spinner:
    """spinner modified from:
    https://raw.githubusercontent.com/Tagar/stuff/master/spinner.py
    """

    def __init__(self, message, delay=0.1):
        self.spinner = itertools.cycle([f"{c}  " for c in "⣾⣽⣻⢿⡿⣟⣯⣷"])
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        self.message = message
        # sys.stdout.write(message)
        echo(message + "  ", newline=False)

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                sys.stdout.write(next(self.spinner))
                self.spinner_visible = True
                sys.stdout.flush()

    def remove_spinner(self, cleanup=False):
        with self._screen_lock:
            if self.spinner_visible:
                sys.stdout.write("\b\b\b")
                # sys.stdout.write("\b")
                self.spinner_visible = False
                if cleanup:
                    sys.stdout.write("   ")  # overwrite spinner with blank
                    # sys.stdout.write("\r")  # move to next line
                    # move back then delete the line
                    sys.stdout.write("\r\033[K")
                sys.stdout.flush()

    def spinner_task(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            self.remove_spinner()

    def __enter__(self):
        if sys.stdout.isatty():
            self._screen_lock = threading.Lock()
            self.busy = True
            self.thread = threading.Thread(target=self.spinner_task)
            self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_traceback):  # noqa
        if sys.stdout.isatty():
            self.busy = False
            self.remove_spinner(cleanup=True)
        else:
            sys.stdout.write("\r")


BOX: Dict[str, str] = {
    "v": "│",
    "h": "─",
    "tl": "╭",
    "tr": "╮",
    "bl": "╰",
    "br": "╯",
    "sep": "┆",
}


@dataclass
class Ansi:
    """control ouptut of ansi(VT100) control codes"""

    bold: str = "\033[1m"
    dim: str = "\033[2m"
    underline: str = "\033[4m"
    red: str = "\033[1;31m"
    green: str = "\033[1;32m"
    yellow: str = "\033[1;33m"
    magenta: str = "\033[1;35m"
    cyan: str = "\033[1;36m"
    end: str = "\033[0m"

    # for argparse help
    header: str = cyan
    option: str = yellow
    metavar: str = "\033[33m"  # normal yellow

    def __post_init__(self):
        if os.getenv("NO_COLOR") or not sys.stdout.isatty():
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

    def tagline(self):
        """generate the viv tagline!"""

        return " ".join(
            (
                self.style(f, "magenta") + self.style(rest, "cyan")
                for f, rest in (("V", "iv"), ("i", "sn't"), ("v", "env!"))
            )
        )

    def subprocess(self, output):
        """generate output for subprocess error

        Args:
            output: text output from subprocess, usually from p.stdout
        """

        new_output = [f"{self.red}->{self.end} {line}" for line in output.splitlines()]

        sys.stdout.write("\n".join(new_output) + "\n")

    def _get_column_size(self, sizes, row):
        for i, length in enumerate(len(cell) for cell in row):
            if length > sizes[i]:
                sizes[i] = length
        return sizes

    def _make_row(self, row) -> str:
        return f"  {BOX['v']} " + f" {BOX['sep']} ".join(row) + f" {BOX['v']}"

    def _sanitize_row(self, sizes: List[int], row: Tuple[str]) -> Tuple[Tuple[str]]:
        if len(row[1]) > sizes[1]:
            return zip_longest(
                (row[0],),
                wrap(row[1], break_on_hyphens=False, width=sizes[1]),
                fillvalue="",
            )
        else:
            return (row,)

    def table(self, rows, header_style="cyan") -> None:
        """generate a table with outline and styled header

        Args:
            rows: sequence of the rows, first item assumed to be header
            header_style: color/style for header row
        """

        sizes = [0] * len(rows[0])
        for row in rows:
            sizes = self._get_column_size(sizes, row)

        col1_limit = shutil.get_terminal_size().columns - 20
        if col1_limit < 20:
            error("increase screen size to view table", code=1)

        if sizes[1] > col1_limit:
            sizes[1] = col1_limit

        # this is maybe taking comprehensions too far....

        table_rows = (
            self._make_row(row)
            for row in (
                # header row
                (
                    self.__dict__[header_style] + f"{cell:<{sizes[i]}}" + self.end
                    for i, cell in enumerate(rows[0])
                ),
                *(
                    (f"{cell:<{sizes[i]}}" for i, cell in enumerate(row))
                    for row in (
                        newrow
                        for row in rows[1:]
                        for newrow in self._sanitize_row(sizes, row)
                    )
                ),
            )
        )

        sys.stdout.write(f"  {BOX['tl']}{BOX['h']*(sum(sizes)+5)}{BOX['tr']}\n")
        sys.stdout.write("\n".join(table_rows) + "\n")
        sys.stdout.write(f"  {BOX['bl']}{BOX['h']*(sum(sizes)+5)}{BOX['br']}\n")


a = Ansi()


def error(msg, code: int = 0):
    """output error message and if code provided exit"""
    echo(f"{a.red}error:{a.end} {msg}", style="red")
    if code:
        sys.exit(code)


def warn(msg):
    """output warning message to stdout"""
    echo(f"{a.yellow}warn:{a.end} {msg}", style="yellow")


def echo(msg: str, style="magenta", newline=True) -> None:
    """output general message to stdout"""
    output = f"{a.cyan}Viv{a.end}{a.__dict__[style]}::{a.end} {msg}"
    if newline:
        output += "\n"
    sys.stdout.write(output)


def run(
    command: List[str | Path],
    spinmsg: str = "",
    clean_up_path: Path | None = None,
    verbose: bool = False,
    ignore_error: bool = False,
    check_output=False,
) -> str:
    """run a subcommand

    Args:
        command: Subcommand to be run in subprocess.
        verbose: If true, print subcommand output.
    """

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
        error("subprocess failed")
        echo("see below for command output", style="red")
        a.subprocess(p.stdout)

        if clean_up_path and clean_up_path.is_dir():
            shutil.rmtree(str(clean_up_path))

        sys.exit(p.returncode)

    elif check_output:
        return p.stdout

    else:
        return ""


def get_hash(spec: Tuple[str, ...] | List[str], track_exe: bool = False) -> str:
    """generate a hash of package specifications

    Args:
        spec: sequence of package specifications
        track_exe: if true add python executable to hash
    Returns:
        sha256 representation of dependencies for vivenv
    """
    pkg_hash = hashlib.sha256()
    pkg_hash.update(str(spec).encode())

    # generate unique venvs for unique python exe's
    if track_exe:
        pkg_hash.update(str(Path(sys.executable).resolve()).encode())

    return pkg_hash.hexdigest()


class ViVenv:
    def __init__(
        self,
        spec: List[str],
        track_exe: bool = False,
        id: str | None = None,
        name: str = "",
        path: Path | None = None,
    ) -> None:
        self.spec = spec
        self.exe = str(Path(sys.executable).resolve()) if track_exe else "N/A"
        self.id = id if id else get_hash(spec, track_exe)
        self.name = name if name else self.id
        self.path = path if path else c.venvcache / self.name

    @classmethod
    def load(cls, name: str) -> "ViVenv":
        """generate a vivenv from a viv-info.json file
        Args:
            name: used as lookup in the vivenv cache
        """
        if not (c.venvcache / name / "viv-info.json").is_file():
            warn(f"possibly corrupted vivenv: {name}")
            return cls(name=name, spec=[""])
        else:
            with (c.venvcache / name / "viv-info.json").open("r") as f:
                venvconfig = json.load(f)

        vivenv = cls(name=name, spec=venvconfig["spec"], id=venvconfig["id"])
        vivenv.exe = venvconfig["exe"]

        return vivenv

    def create(self) -> None:
        echo(f"new unique vivenv -> {self.name}")
        with Spinner("creating vivenv"):
            builder = venv.EnvBuilder(with_pip=True, clear=True)
            builder.create(self.path)

            # add config to ignore pip version
            with (self.path / "pip.conf").open("w") as f:
                f.write("[global]\ndisable-pip-version-check = true")

    def install_pkgs(self):
        cmd: List[str | Path] = [
            self.path / "bin" / "pip",
            "install",
            "--force-reinstall",
        ] + self.spec

        run(
            cmd,
            spinmsg="installing packages in vivenv",
            clean_up_path=self.path,
            verbose=bool(os.getenv("VIV_VERBOSE")),
        )

    def dump_info(self, write=False):
        # TODO: include associated files in 'info'
        # means it needs to be loaded first
        info = {
            "created": str(datetime.today()),
            "id": self.id,
            "spec": self.spec,
            "exe": self.exe,
        }
        # save metadata to json file
        if write:
            with (self.path / "viv-info.json").open("w") as f:
                json.dump(info, f)
        else:
            info["spec"] = ", ".join(self.spec)
            a.table((("key", "value"), *((k, v) for k, v in info.items())))


def activate(*packages: str, track_exe: bool = False, name: str = "") -> None:
    """create a vivenv and append to sys.path

    Args:
        packages: package specifications with optional version specifiers
        track_exe: if true make env python exe specific
        name: use as vivenv name, if not provided id is used
    """
    validate_spec(packages)
    vivenv = ViVenv(list(packages), track_exe=track_exe, name=name)

    if vivenv.name not in [d.name for d in c.venvcache.iterdir()] or os.getenv(
        "VIV_FORCE"
    ):
        vivenv.create()
        vivenv.install_pkgs()
        vivenv.dump_info(write=True)

    modify_sys_path(vivenv.path)


def validate_spec(spec):
    """ensure spec is at least of sequence of strings

    Args:
        spec: sequence of package specifications
    """
    # ? make this a part of ViVenv?
    if not set(map(type, spec)) == {str}:
        error("unexepected input in package spec")
        error(f"check your packages definitions: {spec}", code=1)


def modify_sys_path(new_path: Path):
    # remove user-site
    for i, path in enumerate(sys.path):
        if path == site.USER_SITE:
            sys.path.pop(i)

    sys.path.append(
        str([p for p in (new_path / "lib").glob("python*/site-packages")][0])
    )


def get_venvs():
    vivenvs = {}
    for p in c.venvcache.iterdir():
        vivenv = ViVenv.load(p.name)
        vivenvs[vivenv.name] = vivenv
    return vivenvs


SYS_PATH_TEMPLATE = """__import__("sys").path.append("{path_to_viv}")  # noqa"""
REL_SYS_PATH_TEMPLATE = """__import__("sys").path.append(__import__("os").path.expanduser("{path_to_viv}"))  # noqa"""
IMPORT_TEMPLATE = """__import__("viv").activate({spec})  # noqa"""


def spec_to_import(spec: List[str]) -> None:
    spec_str = ", ".join(f'"{pkg}"' for pkg in spec)
    sys.stdout.write(IMPORT_TEMPLATE.format(spec=spec_str) + "\n")


def freeze_venv(spec: List[str], path: Path | None = None):
    vivenv = ViVenv(spec, track_exe=False, path=path)

    vivenv.create()
    # populate the environment for now use
    # custom cmd since using requirements file
    cmd = [
        vivenv.path / "bin" / "pip",
        "install",
        "--force-reinstall",
    ] + spec

    run(cmd, spinmsg="resolving dependencies", clean_up_path=vivenv.path)

    # generate a frozen environment
    cmd = [vivenv.path / "bin" / "pip", "freeze"]
    resolved_spec = run(cmd, check_output=True)
    return vivenv, resolved_spec


def generate_import(
    requirements: Path, reqs: List[str], vivenvs, include_path: bool, keep: bool
) -> None:
    # TODO: make compatible with Venv class for now just use the name /tmp/
    reqs_from_file = []

    if requirements:
        with requirements.open("r") as f:
            reqs_from_file = f.readlines()

    # refactor to make the below steps context dependent with tmpdir path
    if keep:
        # TODO: remove directory if any errors occur?
        echo("generating new vivenv")
        vivenv, resolved_spec = freeze_venv(reqs + reqs_from_file)

        # update id and move vivenv
        vivenv.spec = resolved_spec.splitlines()
        vivenv.id = get_hash(resolved_spec.splitlines())
        echo(f"updated hash -> {vivenv.id}")

        if not (c.venvcache / vivenv.id).exists():
            vivenv.path = vivenv.path.rename(c.venvcache / vivenv.id)
            vivenv.dump_info(write=True)
        else:
            echo("this vivenv already exists cleaning up temporary vivenv")
            shutil.rmtree(vivenv.path)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:  #
            echo("generating temporary vivenv ")
            vivenv, resolved_spec = freeze_venv(
                reqs + reqs_from_file, path=Path(tmpdir)
            )

    echo("see below for import statements\n")
    if include_path == "absolute":
        sys.stdout.write(
            SYS_PATH_TEMPLATE.format(
                path_to_viv=Path(__file__).resolve().absolute().parent.parent
            )
            + "\n"
        )
    elif include_path == "relative":
        sys.stdout.write(
            REL_SYS_PATH_TEMPLATE.format(
                path_to_viv=str(
                    Path(__file__).resolve().absolute().parent.parent
                ).replace(str(Path.home()), "~")
            )
            + "\n"
        )

    spec_to_import(resolved_spec.splitlines())


class CustomHelpFormatter(RawDescriptionHelpFormatter, HelpFormatter):
    """formatter to remove extra metavar on short opts"""

    def _get_invocation_length(self, invocation):
        return len(a.escape(invocation))

    def _format_action_invocation(self, action):
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

    def _format_usage(self, *args, **kwargs):
        formatted_usage = super()._format_usage(*args, **kwargs)
        # patch usage with color formatting
        formatted_usage = (
            formatted_usage
            if f"{a.header}usage{a.end}:" in formatted_usage
            else formatted_usage.replace("usage:", f"{a.header}usage{a.end}:")
        )
        return formatted_usage

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        action_header_len = len(a.escape(action_header))

        # no help; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup
        # short action name; start on the same line and pad two spaces
        elif action_header_len <= action_width:
            tup = self._current_indent, "", action_width, action_header
            action_header = (
                f"{' '*self._current_indent}{action_header}"
                f"{' '*(action_width+2 - action_header_len)}"
            )
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup
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

    def start_section(self, heading: str) -> None:
        return super().start_section(a.style(heading, style="header"))

    def add_argument(self, action):
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


class ArgumentParser(StdArgParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formatter_class = lambda prog: CustomHelpFormatter(
            prog, max_help_position=35
        )

    def error(self, message):
        error(message)
        echo("see below for help\n", style="red")
        self.print_help()
        sys.exit(2)


description = f"""

{a.tagline()}

{a.style('create/activate a vivenv','underline')}
from command line:
  `{a.style("viv -h","bold")}`
within python script:
  {a.style('__import__("viv").activate("typer", "rich-click")','bold')}
"""


class Viv:
    def __init__(self):
        self.vivenvs = get_venvs()

    def _match_vivenv(self, name_id: str) -> ViVenv:
        # TODO: improve matching algorithm to favor names over id's
        matches = []
        for k, v in self.vivenvs.items():
            if name_id == k or v.name == name_id:
                matches.append(v)
            elif k.startswith(name_id) or v.id.startswith(name_id):
                matches.append(v)
            elif v.name.startswith(name_id):
                matches.append(v)
        if not matches:
            error(f"no matches found for {name_id}", code=1)
        elif len(matches) > 1:
            echo(f"matches {','.join((match.name for match in matches))}", style="red")
            error("too many matches maybe try a longer name?", code=1)
        else:
            return matches[0]

    def remove(self, args):
        """\
        remove a vivenv

        To remove all viv venvs:
        `viv rm $(viv l -q)`
        """

        for name in args.vivenv:
            vivenv = self._match_vivenv(name)
            if vivenv.path.is_dir():
                echo(f"removing {vivenv.name}")
                shutil.rmtree(vivenv.path)
            else:
                error(
                    f"cowardly exiting because I didn't find vivenv: {name}",
                    code=1,
                )

    def freeze(self, args):
        """create import statement from package spec"""

        if not args.reqs:
            print("must specify a requirement")
            sys.exit(1)

        generate_import(
            args.requirements, args.reqs, self.vivenvs, args.path, args.keep
        )

    def list(self, args):
        """list all vivenvs"""

        if args.quiet:
            sys.stdout.write("\n".join(self.vivenvs) + "\n")
        elif len(self.vivenvs) == 0:
            echo("no vivenvs setup")
        else:
            rows = (
                ("vivenv", "spec"),
                *(
                    (
                        f"{vivenv.name[:6]}..."
                        if len(vivenv.name) > 9
                        else vivenv.name,
                        ", ".join(vivenv.spec),
                    )
                    for vivenv in self.vivenvs.values()
                ),
            )
            a.table(rows)

    def exe(self, args):
        """run python/pip in vivenv"""

        vivenv = self._match_vivenv(args.vivenv)

        pip_path, python_path = (vivenv.path / "bin" / cmd for cmd in ("pip", "python"))
        # todo check for vivenv
        print(f"executing command within {args.vivenv}")

        cmd = (
            f"{pip_path} {' '.join(args.cmd)}"
            if args.exe == "pip"
            else f"{python_path} {' '.join(args.cmd)}"
        )

        echo(f"executing {cmd}")
        run(shlex.split(cmd), verbose=True)

    def info(self, args):
        """get metadata about a vivenv"""
        vivenv = self._match_vivenv(args.vivenv)
        metadata_file = vivenv.path / "viv-info.json"

        if not metadata_file.is_file():
            error(f"Unable to find metadata for vivenv: {args.vivenv}", code=1)

        echo(f"more info about {vivenv.name}:")

        vivenv.dump_info()

    def _get_subcmd_parser(self, subparsers, name: str, **kwargs) -> ArgumentParser:
        aliases = kwargs.pop("aliases", [name[0]])
        cmd = getattr(self, name)
        parser = subparsers.add_parser(
            name,
            help=cmd.__doc__.splitlines()[0],
            description=dedent(cmd.__doc__),
            aliases=aliases,
            **kwargs,
        )
        parser.set_defaults(func=cmd)

        return parser

    def cli(self):
        """cli entrypoint"""

        parser = ArgumentParser(description=description)
        parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"{a.bold}viv{a.end}, version {a.cyan}{__version__}{a.end}",
        )

        subparsers = parser.add_subparsers(
            metavar="<sub-cmd>", title="subcommands", required=True
        )
        p_vivenv_arg = ArgumentParser(add_help=False)
        p_vivenv_arg.add_argument("vivenv", help="name/hash of vivenv")
        p_list = self._get_subcmd_parser(
            subparsers,
            "list",
        )

        p_list.add_argument(
            "-q",
            "--quiet",
            help="suppress non-essential output",
            action="store_true",
            default=False,
        )

        p_exe = self._get_subcmd_parser(
            subparsers,
            "exe",
        )
        p_exe_sub = p_exe.add_subparsers(
            title="subcommand", metavar="<sub-cmd>", required=True
        )

        p_exe_shared = ArgumentParser(add_help=False)
        p_exe_shared.add_argument(
            "cmd",
            help="command to to execute",
            nargs="*",
        )

        p_exe_python = p_exe_sub.add_parser(
            "python",
            help="run command with python",
            parents=[p_vivenv_arg, p_exe_shared],
        )
        p_exe_pip = p_exe_sub.add_parser(
            "pip", help="run command with pip", parents=[p_vivenv_arg, p_exe_shared]
        )
        p_exe_python.set_defaults(func=self.exe, exe="python")
        p_exe_pip.set_defaults(func=self.exe, exe="pip")

        p_remove = self._get_subcmd_parser(
            subparsers,
            "remove",
            aliases=["rm"],
        )

        p_remove.add_argument("vivenv", help="name/hash of vivenv", nargs="*")
        p_freeze = self._get_subcmd_parser(
            subparsers,
            "freeze",
        )
        p_freeze.add_argument(
            "-p",
            "--path",
            help="generate line to add viv to sys.path",
            choices=["absolute", "relative"],
        )
        p_freeze.add_argument(
            "-r",
            "--requirements",
            help="path to requirements.txt file",
            metavar="<path>",
        )
        p_freeze.add_argument(
            "-k",
            "--keep",
            help="preserve environment",
            action="store_true",
        )
        p_freeze.add_argument("reqs", help="requirements specifiers", nargs="*")

        self._get_subcmd_parser(
            subparsers,
            "info",
            parents=[p_vivenv_arg],
        )

        args = parser.parse_args()

        args.func(args)


def main():
    viv = Viv()
    viv.cli()


if __name__ == "__main__":
    main()
