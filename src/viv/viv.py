#!/usr/bin/env python3
"""Viv isn't venv!

  viv -h
    OR
  __import__("viv").use("requests", "bs4")
"""

from __future__ import annotations

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
from argparse import (
    SUPPRESS,
    Action,
    HelpFormatter,
    Namespace,
    RawDescriptionHelpFormatter,
    _SubParsersAction,
)
from argparse import ArgumentParser as StdArgParser
from dataclasses import dataclass
from datetime import datetime
from itertools import zip_longest
from pathlib import Path
from textwrap import dedent, fill, wrap
from types import TracebackType
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NoReturn,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
)
from urllib.error import HTTPError
from urllib.request import urlopen

__version__ = "23.5a1-17-gea9a184-dev"


class Config:
    """viv config manager"""

    def __init__(self) -> None:
        self._cache = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "viv"

    def _ensure(self, p: Path) -> Path:
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def venvcache(self) -> Path:
        return self._ensure(self._cache / "venvs")

    @property
    def srccache(self) -> Path:
        return self._ensure(self._cache / "src")

    @property
    def binparent(self) -> Path:
        return self._ensure(
            Path(os.getenv("VIV_BIN_DIR", Path.home() / ".local" / "bin"))
        )

    @property
    def srcdefault(self) -> Path:
        parent = (
            Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "viv"
        )
        return self._ensure(parent) / "viv.py"


c = Config()


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
        # sys.stdout.write(message)
        echo(message + "  ", newline=False)

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
            time.sleep(self.delay)
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

    def __post_init__(self) -> None:
        if os.getenv("NO_COLOR") or not sys.stderr.isatty():
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

    def tagline(self) -> str:
        """generate the viv tagline!"""

        return " ".join(
            (
                self.style(f, "magenta") + self.style(rest, "cyan")
                for f, rest in (("V", "iv"), ("i", "sn't"), ("v", "env!"))
            )
        )

    def subprocess(self, output: str) -> None:
        """generate output for subprocess error

        Args:
            output: text output from subprocess, usually from p.stdout
        """

        echo("subprocess output:")
        new_output = [f"{self.red}->{self.end} {line}" for line in output.splitlines()]
        sys.stdout.write("\n".join(new_output) + "\n")

    def _get_column_sizes(
        self, rows: Tuple[Tuple[str, Sequence[str]], ...]
    ) -> List[int]:
        """convert list of rows to list of columns sizes

        First convert rows into list of columns,
        then get max string length for each column.
        """
        return list(max(map(len, lst)) for lst in map(list, zip(*rows)))  # type: ignore

    def _make_row(self, row: Generator[Any, None, None]) -> str:
        return f"  {BOX['v']} " + f" {BOX['sep']} ".join(row) + f" {BOX['v']}"

    def _sanitize_row(
        self, sizes: List[int], row: Tuple[str, Sequence[str]]
    ) -> Tuple[Tuple[str, Sequence[str]], ...]:
        if len(row[1]) > sizes[1]:
            return tuple(
                zip_longest(
                    (row[0],),
                    wrap(str(row[1]), break_on_hyphens=False, width=sizes[1]),
                    fillvalue="",
                )
            )
        else:
            return (row,)

    def viv_preamble(self, style: str = "magenta", sep: str = "::") -> str:
        return f"{self.cyan}Viv{self.end}{self.__dict__[style]}{sep}{self.end}"

    def table(
        self, rows: Tuple[Tuple[str, Sequence[str]], ...], header_style: str = "cyan"
    ) -> None:
        """generate a table with outline and styled header assumes two columns

        Args:
            rows: sequence of the rows, first item assumed to be header
            header_style: color/style for header row
        """

        sizes = self._get_column_sizes(rows)

        col2_limit = shutil.get_terminal_size().columns - 20
        if col2_limit < 20:
            error("increase screen size to view table", code=1)
        elif sizes[1] > col2_limit:
            sizes[1] = col2_limit

        header, rows = rows[0], rows[1:]
        # this is maybe taking comprehensions too far....
        table_rows = (
            self._make_row(row)
            for row in (
                # header row
                (
                    self.__dict__[header_style] + f"{cell:<{sizes[i]}}" + self.end
                    for i, cell in enumerate(header)
                ),
                # rest of the rows
                *(
                    (f"{cell:<{sizes[i]}}" for i, cell in enumerate(row))
                    for row in (
                        newrow
                        for row in rows
                        for newrow in self._sanitize_row(sizes, row)
                    )
                ),
            )
        )

        sys.stderr.write(f"  {BOX['tl']}{BOX['h']*(sum(sizes)+5)}{BOX['tr']}\n")
        sys.stderr.write("\n".join(table_rows) + "\n")
        sys.stderr.write(f"  {BOX['bl']}{BOX['h']*(sum(sizes)+5)}{BOX['br']}\n")


a = Ansi()


# TODO: convet the below functions into a proper file/stream logging interface
def echo(
    msg: str, style: str = "magenta", newline: bool = True, fd: TextIO = sys.stderr
) -> None:
    """output general message to stdout"""
    output = f"{a.viv_preamble(style)} {msg}"
    if newline:
        output += "\n"
    fd.write(output)


def error(msg: str, code: int = 0) -> None:
    """output error message and if code provided exit"""
    echo(f"{a.red}error:{a.end} {msg}", style="red")
    if code:
        sys.exit(code)


def warn(msg: str) -> None:
    """output warning message to stdout"""
    echo(f"{a.yellow}warn:{a.end} {msg}", style="yellow")


def confirm(question: str, context: str = "") -> bool:
    sys.stderr.write(context)
    sys.stderr.write(
        a.viv_preamble(sep="?? ") + question + a.style(" (Y)es/(n)o ", "yellow")
    )
    while True:
        ans = input().strip().lower()
        if ans in ("y", "yes"):
            return True
        elif ans in ("n", "no"):
            return False
        sys.stdout.write("Please select (Y)es or (n)o. ")
    sys.stdout.write("\n")


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


class ArgumentParser(StdArgParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.formatter_class = lambda prog: CustomHelpFormatter(
            prog,
            max_help_position=35,
        )

    def error(self, message: str) -> NoReturn:
        error(message)
        echo(f"see `{self.prog} --help` for more info", style="red")
        sys.exit(2)


def run(
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

    sha256 = hashlib.sha256()
    sha256.update(
        (
            str(spec) + (str(Path(sys.executable).resolve()) if track_exe else "N/A")
        ).encode()
    )

    return sha256.hexdigest()


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

    def create(self, quiet: bool = False) -> None:
        if not quiet:
            echo(f"new unique vivenv -> {self.name}")
        with Spinner("creating vivenv"):
            builder = venv.EnvBuilder(with_pip=True, clear=True)
            builder.create(self.path)

            # add config to ignore pip version
            with (self.path / "pip.conf").open("w") as f:
                f.write("[global]\ndisable-pip-version-check = true")

    def install_pkgs(self) -> None:
        cmd: List[str] = [
            str(self.path / "bin" / "pip"),
            "install",
            "--force-reinstall",
        ] + self.spec

        run(
            cmd,
            spinmsg="installing packages in vivenv",
            clean_up_path=self.path,
            verbose=bool(os.getenv("VIV_VERBOSE")),
        )

    def dump_info(self, write: bool = False) -> None:
        # TODO: include associated files in 'info'
        # means it needs to be loaded first
        # or keep a seperate file hash in c.share?
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


def use(*packages: str, track_exe: bool = False, name: str = "") -> Path:
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
    return vivenv.path


def validate_spec(spec: Tuple[str, ...]) -> None:
    """ensure spec is at least of sequence of strings

    Args:
        spec: sequence of package specifications
    """
    # ? make this a part of ViVenv?
    if not set(map(type, spec)) == {str}:
        error("unexepected input in package spec")
        error(f"check your packages definitions: {spec}", code=1)


def modify_sys_path(new_path: Path) -> None:
    # remove user-site
    for i, path in enumerate(sys.path):
        if path == site.USER_SITE:
            sys.path.pop(i)

    sys.path.append(
        str([p for p in (new_path / "lib").glob("python*/site-packages")][0])
    )


def get_venvs() -> Dict[str, ViVenv]:
    vivenvs = {}
    for p in c.venvcache.iterdir():
        vivenv = ViVenv.load(p.name)
        vivenvs[vivenv.name] = vivenv
    return vivenvs


# TODO: make a template class?

SYS_PATH_TEMPLATE = """__import__("sys").path.append("{path_to_viv}")  # noqa"""
REL_SYS_PATH_TEMPLATE = (
    """__import__("sys").path.append(__import__("os")"""
    """.path.expanduser("{path_to_viv}"))  # noqa"""
)
IMPORT_TEMPLATE = """__import__("viv").use({spec})  # noqa"""

STANDALONE_TEMPLATE = r"""
# <<<<< auto-generated by viv (v{version})
# see `python3 <(curl -fsSL gh.dayl.in/viv/viv.py) --help`
# fmt: off
{func}
# fmt: on
# >>>>> code golfed with <3
"""  # noqa

STANDALONE_TEMPLATE_FUNC = r"""def _viv_use(*pkgs, track_exe=False, name=""):
    T,F=True,False;i,s,m,e,spec=__import__,str,map,lambda x: T if x else F,[*pkgs]
    if not {*m(type,pkgs)}=={s}: raise ValueError(f"spec: {pkgs} is invalid")
    ge,sys,P,ew=i("os").getenv,i("sys"),i("pathlib").Path,i("sys").stderr.write
    (cache:=(P(ge("XDG_CACHE_HOME",P.home()/".cache"))/"viv"/"venvs")).mkdir(parents=T,exist_ok=T)
    ((sha256:=i("hashlib").sha256()).update((s(spec)+
     (((exe:=("N/A",s(P(i("sys").executable).resolve()))[e(track_exe)])))).encode()))
    if ((env:=cache/(name if name else (_id:=sha256.hexdigest())))
        not in cache.glob("*/")) or ge("VIV_FORCE"):
        v=e(ge("VIV_VERBOSE"));ew(f"generating new vivenv -> {env.name}\n")
        i("venv").EnvBuilder(with_pip=T,clear=T).create(env)
        with (env/"pip.conf").open("w") as f:f.write("[global]\ndisable-pip-version-check=true")
        if (p:=i("subprocess").run([env/"bin"/"pip","install","--force-reinstall",*spec],text=True,
            stdout=(-1,None)[v],stderr=(-2,None)[v])).returncode!=0:
            if env.is_dir():i("shutil").rmtree(env)
            ew(f"pip had non zero exit ({p.returncode})\n{p.stdout}\n");sys.exit(p.returncode)
        with (env/"viv-info.json").open("w") as f:
            i("json").dump({"created":s(i("datetime").datetime.today()),
            "id":_id,"spec":spec,"exe":exe},f)
    sys.path = [p for p in (*sys.path,s(*(env/"lib").glob("py*/si*"))) if p!=i("site").USER_SITE]
    return env
"""  # noqa

SHOW_TEMPLATE = f"""
  {a.style('Version', 'bold')}: {{version}}
  {a.style('CLI', 'bold')}: {{cli}}
  {a.style('Running Source', 'bold')}: {{running_src}}
  {a.style('Local Source', 'bold')}: {{local_src}}
"""

INSTALL_TEMPLATE = f"""
  Install viv.py to {a.green}{{src_location}}{a.end}
  Symlink {a.bold}{{src_location}}{a.end} to {a.bold}{{cli_location}}{a.end}

"""

UPDATE_TEMPLATE = f"""
  Update source at {a.green}{{src_location}}{a.end}
  Symlink {a.bold}{{src_location}}{a.end} to {a.bold}{{cli_location}}{a.end}
  Version {a.bold}{{local_version}}{a.end} -> {a.bold}{{next_version}}{a.end}

"""

SHIM_TEMPLATE = """\
#!/usr/bin/env python3

{imports}
import subprocess
import sys

if __name__ == "__main__":
    vivenv = {use}
    sys.exit(subprocess.run([vivenv / "bin" / "{bin}", *sys.argv[1:]]).returncode)
"""

DESCRIPTION = f"""

{a.tagline()}
to create/activate a vivenv:
- from command line: `{a.style("viv -h","bold")}`
- within python script: {a.style('__import__("viv").use("typer", "rich-click")','bold')}
"""


def noqa(txt: str) -> str:
    max_length = max(map(len, txt.splitlines()))
    return "\n".join((f"{line:{max_length}} # noqa" for line in txt.splitlines()))


def spec_to_import(spec: List[str]) -> None:
    spec_str = ", ".join(f'"{pkg}"' for pkg in spec)
    sys.stdout.write(IMPORT_TEMPLATE.format(spec=spec_str) + "\n")


def combined_spec(reqs: List[str], requirements: Path) -> List[str]:
    if requirements:
        with requirements.open("r") as f:
            reqs += f.readlines()

    return reqs


def resolve_deps(args: Namespace):
    spec = combined_spec(args.reqs, args.requirements)

    with tempfile.TemporaryDirectory(prefix="viv-") as tmpdir:
        echo("generating frozen spec")
        vivenv = ViVenv(spec, track_exe=False, path=Path(tmpdir))

        vivenv.create(quiet=True)
        # populate the environment for now use
        # custom cmd since using requirements file
        cmd = [
            str(vivenv.path / "bin" / "pip"),
            "install",
            "--force-reinstall",
        ] + spec

        run(cmd, spinmsg="resolving dependencies", clean_up_path=vivenv.path)

        cmd = [str(vivenv.path / "bin" / "pip"), "freeze"]
        resolved_spec = run(cmd, check_output=True)
    return resolved_spec.splitlines()


def generate_import(
    args: Namespace,
) -> None:
    spec = resolve_deps(args)
    if args.keep:
        # re-create env again since path's are hard-coded
        vivenv = ViVenv(spec)

        if vivenv.name not in [d.name for d in c.venvcache.iterdir()] or os.getenv(
            "VIV_FORCE"
        ):
            vivenv.create()
            vivenv.install_pkgs()
            vivenv.dump_info(write=True)

        else:
            echo("re-using existing vivenv")

    echo("see below for import statements\n")

    if args.standalone:
        sys.stdout.write(
            STANDALONE_TEMPLATE.format(
                version=__version__,
                func=noqa(
                    STANDALONE_TEMPLATE_FUNC
                    + "_viv_use("
                    + fill(
                        ", ".join(f'"{pkg}"' for pkg in spec),
                        width=100,
                        subsequent_indent="    ",
                    )
                    + ")"
                ),
            )
            + "\n"
        )
        return

    if args.path:
        if args.path == "abs":
            sys.stdout.write(
                SYS_PATH_TEMPLATE.format(
                    path_to_viv=Path(__file__).resolve().absolute().parent.parent
                )
                + "\n"
            )
        elif args.path == "rel":
            sys.stdout.write(
                REL_SYS_PATH_TEMPLATE.format(
                    path_to_viv=str(
                        Path(__file__).resolve().absolute().parent.parent
                    ).replace(str(Path.home()), "~")
                )
                + "\n"
            )

    spec_to_import(spec)


def fetch_source(reference: str) -> str:
    try:
        r = urlopen(
            "https://raw.githubusercontent.com/daylinmorgan/viv/"
            + reference
            + "/src/viv/viv.py"
        )
    except HTTPError as e:
        error(
            "Issue updating viv see below:"
            + a.style("->  ", "red").join(["\n"] + repr(e).splitlines())
        )
        if "404" in repr(e):
            echo("Please check your reference is valid.", style="red")
        sys.exit(1)

    src = r.read()
    (hash := hashlib.sha256()).update(src)
    sha256 = hash.hexdigest()

    cached_src_file = c.srccache / f"{sha256}.py"

    if not cached_src_file.is_file():
        with cached_src_file.open("w") as f:
            f.write(src.decode())

    return sha256


def make_executable(path: Path) -> None:
    """apply an executable bit for all users with read access"""
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2  # copy R bits to X
    os.chmod(path, mode)


class Viv:
    def __init__(self) -> None:
        self.vivenvs = get_venvs()
        self._get_sources()
        self.name = (
            "viv" if self.local else "python3 <(curl -fsSL gh.dayl.in/viv/viv.py)"
        )

    def _get_sources(self) -> None:
        self.local_source: Optional[Path] = None
        self.running_source = Path(__file__).resolve()
        self.local = not str(self.running_source).startswith("/proc/")
        if self.local:
            self.local_source = self.running_source
            self.local_version = __version__
        else:
            try:
                _local_viv = __import__("viv")
                self.local_source = (
                    Path(_local_viv.__file__) if _local_viv.__file__ else None
                )
                self.local_version = _local_viv.__version__
            except ImportError:
                self.local_version = "Not Found"

        if self.local_source:
            self.git = (self.local_source.parent.parent.parent / ".git").is_dir()
        else:
            self.git = False

    def _check_local_source(self, args: Namespace) -> None:
        if not self.local_source and not (args.standalone or args.path):
            warn(
                "failed to find local copy of `viv` "
                "make sure to add it to your PYTHONPATH "
                "or consider using --path/--standalone"
            )

    def _match_vivenv(self, name_id: str) -> ViVenv:  # type: ignore[return]
        # TODO: improve matching algorithm to favor names over id's
        matches: List[ViVenv] = []
        for k, v in self.vivenvs.items():
            if name_id == k or v.name == name_id:
                matches.append(v)
            elif k.startswith(name_id) or v.id.startswith(name_id):
                matches.append(v)
            elif v.name.startswith(name_id):
                matches.append(v)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            echo(f"matches {','.join((match.name for match in matches))}", style="red")
            error("too many matches maybe try a longer name?", code=1)
        else:
            error(f"no matches found for {name_id}", code=1)

    def remove(self, args: Namespace) -> None:
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

    def freeze(self, args: Namespace) -> None:
        """create import statement from package spec"""

        self._check_local_source(args)

        if not args.reqs:
            error("must specify a requirement", code=1)
        if args.path and args.standalone:
            error("-p/--path and -s/--standalone are mutually exclusive", code=1)

        generate_import(
            args,
        )

    def list(self, args: Namespace) -> None:
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

    def exe(self, args: Namespace) -> None:
        """run python/pip in vivenv"""

        vivenv = self._match_vivenv(args.vivenv)

        pip_path, python_path = (vivenv.path / "bin" / cmd for cmd in ("pip", "python"))
        # todo check for vivenv
        echo(f"executing command within {vivenv.name}")

        cmd = (
            f"{pip_path} {' '.join(args.cmd)}"
            if args.exe == "pip"
            else f"{python_path} {' '.join(args.cmd)}"
        )

        echo(f"executing {cmd}")
        run(shlex.split(cmd), verbose=True)

    def info(self, args: Namespace) -> None:
        """get metadata about a vivenv"""
        vivenv = self._match_vivenv(args.vivenv)
        metadata_file = vivenv.path / "viv-info.json"

        if not metadata_file.is_file():
            error(f"Unable to find metadata for vivenv: {args.vivenv}", code=1)

        echo(f"more info about {vivenv.name}:")

        vivenv.dump_info()

    def _install_local_src(self, sha256: str, src: Path, cli: Path) -> None:
        echo("updating local source copy of viv")
        shutil.copy(c.srccache / f"{sha256}.py", src)
        make_executable(src)
        echo("symlinking cli")

        if not cli.is_file():
            cli.symlink_to(src)
        else:
            cli.unlink()
            cli.symlink_to(src)

        echo("Remember to include the following line in your shell rc file:")
        sys.stderr.write(
            '  export PYTHONPATH="$PYTHONPATH:$HOME/'
            f'{src.relative_to(Path.home())}"\n'
        )

    def manage(self, args: Namespace) -> None:
        """manage viv itself"""

        if args.cmd == "show":
            if args.pythonpath:
                if self.local and self.local_source:
                    sys.stdout.write(str(self.local_source.parent) + "\n")
                else:
                    error("expected to find a local installation", code=1)
            else:
                echo("Current:")
                sys.stderr.write(
                    SHOW_TEMPLATE.format(
                        version=__version__,
                        cli=shutil.which("viv"),
                        running_src=self.running_source,
                        local_src=self.local_source,
                    )
                )

        elif args.cmd == "update":
            if not self.local_source:
                error(
                    a.style("viv manage update", "bold")
                    + " should be used with an exisiting installation",
                    1,
                )

            if self.git:
                error(
                    a.style("viv manage update", "bold")
                    + " shouldn't be used with a git-based installation",
                    1,
                )
            sha256 = fetch_source(args.ref)
            sys.path.append(str(c.srccache))
            next_version = __import__(sha256).__version__

            if self.local_version == next_version:
                echo(f"no change between {args.ref} and local version")
                sys.exit(0)

            if confirm(
                "Would you like to perform the above installation steps?",
                UPDATE_TEMPLATE.format(
                    src_location=self.local_source,
                    local_version=self.local_version,
                    cli_location=args.cli,
                    next_version=next_version,
                ),
            ):
                self._install_local_src(
                    sha256,
                    Path(
                        args.src if not self.local_source else self.local_source,
                    ),
                    args.cli,
                )

        elif args.cmd == "install":
            if self.local_source:
                error(f"found existing viv installation at {self.local_source}")
                echo(
                    "use "
                    + a.style("viv manage update", "bold")
                    + " to modify current installation.",
                    style="red",
                )
                sys.exit(1)

            sha256 = fetch_source(args.ref)
            sys.path.append(str(c.srccache))
            downloaded_version = __import__(sha256).__version__
            echo(f"Downloaded version: {downloaded_version}")

            # TODO: see if file is actually where
            # we are about to install and give more instructions

            if confirm(
                "Would you like to perform the above installation steps?",
                INSTALL_TEMPLATE.format(
                    src_location=args.src,
                    cli_location=args.cli,
                ),
            ):
                self._install_local_src(sha256, args.src, args.cli)

    def shim(self, args: Namespace) -> None:
        """\
        generate viv-powered cli apps

        examples:
          viv shim black
          viv shim yartsu -o ~/bin/yartsu --standalone
        """
        self._check_local_source(args)

        if not args.reqs:
            error("please specify at lease one dependency", code=1)

        default_bin = re.split(r"[=><~!*]+", args.reqs[0])[0]
        bin = default_bin if not args.bin else args.bin
        output = (
            c.binparent / default_bin if not args.output else args.output.absolute()
        )

        if output.is_file():
            error(f"{output} already exists...exiting", code=1)

        if args.freeze:
            spec = resolve_deps(args)
        else:
            spec = combined_spec(args.reqs, args.requirements)

        spec_str = ", ".join(f'"{req}"' for req in spec)
        if args.standalone:
            imports = STANDALONE_TEMPLATE.format(
                version=__version__, func=noqa(STANDALONE_TEMPLATE_FUNC)
            )
            use = f"_viv_use({spec_str})"
        elif args.path:
            if not self.local_source:
                error("No local viv found to import from", code=1)
            else:
                imports = (
                    REL_SYS_PATH_TEMPLATE.format(
                        path_to_viv=str(
                            self.local_source.resolve().absolute().parent.parent
                        ).replace(str(Path.home()), "~")
                    )
                    if args.path == "abs"
                    else SYS_PATH_TEMPLATE.format(
                        path_to_viv=self.local_source.resolve().absolute().parent.parent
                    )
                )
                use = IMPORT_TEMPLATE.format(spec=spec_str)
        else:
            imports = ""
            use = IMPORT_TEMPLATE.format(spec=spec_str)

        if confirm(
            f"Write shim for {a.style(bin,'bold')} to {a.style(output,'green')}?"
        ):
            with output.open("w") as f:
                f.write(SHIM_TEMPLATE.format(imports=imports, use=use, bin=bin))

            make_executable(output)

    def _get_subcmd_parser(
        self,
        subparsers: _SubParsersAction[ArgumentParser],
        name: str,
        attr: Optional[str] = None,
        **kwargs: Any,
    ) -> ArgumentParser:
        aliases = kwargs.pop("aliases", [name[0]])
        cmd = getattr(self, attr if attr else name)
        parser: ArgumentParser = subparsers.add_parser(
            name,
            help=cmd.__doc__.splitlines()[0],
            description=dedent(cmd.__doc__),
            aliases=aliases,
            **kwargs,
        )
        parser.set_defaults(func=cmd)

        return parser

    def cli(self) -> None:
        """cli entrypoint"""

        parser = ArgumentParser(prog=self.name, description=DESCRIPTION)
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
        p_list = self._get_subcmd_parser(subparsers, "list")

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

        p_exe_sub.add_parser(
            "python",
            help="run command with python",
            parents=[p_vivenv_arg, p_exe_shared],
        ).set_defaults(func=self.exe, exe="python")

        p_exe_sub.add_parser(
            "pip", help="run command with pip", parents=[p_vivenv_arg, p_exe_shared]
        ).set_defaults(func=self.exe, exe="pip")

        p_remove = self._get_subcmd_parser(
            subparsers,
            "remove",
            aliases=["rm"],
        )

        p_remove.add_argument("vivenv", help="name/hash of vivenv", nargs="*")

        p_freeze_shim_shared = ArgumentParser(add_help=False)

        p_freeze_shim_shared.add_argument(
            "-p",
            "--path",
            help="generate line to add viv to sys.path",
            choices=["abs", "rel"],
        )
        p_freeze_shim_shared.add_argument(
            "-r",
            "--requirements",
            help="path/to/requirements.txt file",
            metavar="<path>",
        )
        p_freeze_shim_shared.add_argument(
            "-k",
            "--keep",
            help="preserve environment",
            action="store_true",
        )
        p_freeze_shim_shared.add_argument(
            "-s",
            "--standalone",
            help="generate standalone activation function",
            action="store_true",
        )
        p_freeze_shim_shared.add_argument(
            "reqs", help="requirements specifiers", nargs="*"
        )

        self._get_subcmd_parser(subparsers, "freeze", parents=[p_freeze_shim_shared])
        self._get_subcmd_parser(
            subparsers,
            "info",
            parents=[p_vivenv_arg],
        )
        p_manage_shared = ArgumentParser(add_help=False)
        p_manage_shared.add_argument(
            "-r",
            "--ref",
            help="git reference (branch/tag/commit)",
            default="latest",
            metavar="<ref>",
        )

        p_manage_shared.add_argument(
            "-s",
            "--src",
            help="path/to/source_file",
            default=c.srcdefault,
            metavar="<src>",
        )
        p_manage_shared.add_argument(
            "-c",
            "--cli",
            help="path/to/cli (symlink to src)",
            default=Path.home() / ".local" / "bin" / "viv",
            metavar="<cli>",
        )

        p_manage_sub = self._get_subcmd_parser(
            subparsers,
            name="manage",
        ).add_subparsers(title="subcommand", metavar="<sub-cmd>", required=True)

        p_manage_sub.add_parser(
            "install", help="install viv", aliases="i", parents=[p_manage_shared]
        ).set_defaults(func=self.manage, cmd="install")

        p_manage_sub.add_parser(
            "update",
            help="update viv version",
            aliases="u",
            parents=[p_manage_shared],
        ).set_defaults(func=self.manage, cmd="update")

        (
            p_manage_show := p_manage_sub.add_parser(
                "show", help="show current installation info", aliases="s"
            )
        ).set_defaults(func=self.manage, cmd="show")

        p_manage_show.add_argument(
            "-p", "--pythonpath", help="show the path/to/install", action="store_true"
        )

        (
            p_manage_shim := self._get_subcmd_parser(
                subparsers, "shim", parents=[p_freeze_shim_shared]
            )
        ).set_defaults(func=self.shim, cmd="shim")
        p_manage_shim.add_argument(
            "-f",
            "--freeze",
            help="freeze/resolve all dependencies",
            action="store_true",
        )
        p_manage_shim.add_argument(
            "-o",
            "--output",
            help="path/to/output file",
            type=Path,
            metavar="<path>",
        )
        p_manage_shim.add_argument(
            "-b", "--bin", help="console_script/script to invoke"
        )

        args = parser.parse_args()

        args.func(args)


def main() -> None:
    viv = Viv()
    viv.cli()


if __name__ == "__main__":
    main()
