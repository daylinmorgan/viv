#!/usr/bin/env python3
"""viv isn't venv!

  viv -h
    OR
  __import__("viv").use("requests", "bs4")
"""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import os
import re
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
from pathlib import Path
from textwrap import dedent, fill
from types import TracebackType
from typing import (
    Any,
    Dict,
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

__version__ = "23.5a5"


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


class Ansi:
    """control ouptut of ansi(VT100) control codes"""

    def __init__(self) -> None:
        self.bold: str = "\033[1m"
        self.dim: str = "\033[2m"
        self.underline: str = "\033[4m"
        self.red: str = "\033[1;31m"
        self.green: str = "\033[1;32m"
        self.yellow: str = "\033[1;33m"
        self.magenta: str = "\033[1;35m"
        self.cyan: str = "\033[1;36m"
        self.end: str = "\033[0m"

        # for argparse help
        self.header: str = self.cyan
        self.option: str = self.yellow
        self.metavar: str = "\033[33m"  # normal yellow

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
                for f, rest in (("v", "iv"), ("i", "sn't"), ("v", "env!"))
            )
        )

    def subprocess(self, command: List[str], output: str) -> None:
        """generate output for subprocess error

        Args:
            output: text output from subprocess, usually from p.stdout
        """
        if not output:
            return

        error("subprocess failed")
        echo("see below for command output", style="red")
        echo(f"cmd:\n  {' '.join(command)}", style="red")
        new_output = [f"{self.red}->{self.end} {line}" for line in output.splitlines()]
        echo("subprocess output:" + "\n".join(("", *new_output, "")), style="red")

    def viv_preamble(self, style: str = "magenta", sep: str = "::") -> str:
        return f"{self.cyan}viv{self.end}{self.__dict__[style]}{sep}{self.end}"


a = Ansi()


class Template:
    description = f"""

{a.tagline()}
to create/activate a vivenv:
- from command line: `{a.style("viv -h","bold")}`
- within python script: {a.style('__import__("viv").use("typer", "rich-click")','bold')}
"""

    _standalone_func = r"""def _viv_use(*pkgs, track_exe=False, name=""):
    import hashlib, json, os, site, shutil, sys, venv  # noqa
    from pathlib import Path  # noqa
    from datetime import datetime  # noqa
    from subprocess import run  # noqa

    if not {*map(type, pkgs)} == {str}:
        raise ValueError(f"spec: {pkgs} is invalid")

    meta = dict.fromkeys(("created", "accessed"), (t := str(datetime.today())))
    runner = str(Path(__file__).absolute().resolve())
    force, verbose, xdg = map(os.getenv, ("VIV_FORCE", "VIV_VERBOSE", "XDG_CACHE_HOME"))
    cache = (Path(xdg) if xdg else Path.home() / ".cache") / "viv" / "venvs"
    cache.mkdir(parents=True, exist_ok=True)
    exe = str(Path(sys.executable).resolve()) if track_exe else "N/A"
    (sha256 := hashlib.sha256()).update((str(spec := [*pkgs]) + exe).encode())
    _id = sha256.hexdigest()
    if (env := cache / (name if name else _id)) not in cache.glob("*/") or force:
        sys.stderr.write(f"generating new vivenv -> {env.name}\n")
        venv.create(env, symlinks=True, with_pip=True, clear=True)
        (env / "pip.conf").write_text("[global]\ndisable-pip-version-check=true")
        run_kw = dict(zip(("stdout", "stderr"), ((None,) * 2 if verbose else (-1, 2))))
        p = run([env / "bin" / "pip", "install", "--force-reinstall", *spec], **run_kw)
        if (rc := p.returncode) != 0:
            if env.is_dir():
                shutil.rmtree(env)
            sys.stderr.write(f"pip had non zero exit ({rc})\n{p.stdout.decode()}\n")
            sys.exit(rc)
        meta.update(dict(id=_id, spec=spec, exe=exe, name=name, files=[runner]))
    else:
        meta = json.loads((env / "vivmeta.json").read_text())
        meta.update(dict(accessed=t, files=sorted({*meta["files"],runner})))

    (env / "vivmeta.json").write_text(json.dumps(meta))
    sys.path = [p for p in sys.path if not p != site.USER_SITE]
    site.addsitedir(str(*(env / "lib").glob("py*/si*")))
    return env
"""

    def noqa(self, txt: str) -> str:
        max_length = max(map(len, txt.splitlines()))
        return "\n".join((f"{line:{max_length}} # noqa" for line in txt.splitlines()))

    def _use_str(self, spec: List[str], standalone: bool = False) -> str:
        spec_str = ", ".join(f'"{req}"' for req in spec)
        if standalone:
            return f"""_viv_use({fill(spec_str,width=90,subsequent_indent="    ",)})"""
        else:
            return f"""__import__("viv").use({spec_str})"""

    def standalone(self, spec: List[str]) -> str:
        func_use = "\n".join(
            (self._standalone_func, self.noqa(self._use_str(spec, standalone=True)))
        )
        return f"""
# AUTOGENERATED by viv (v{__version__})
# see `python3 <(curl -fsSL viv.dayl.in/viv.py) --help`
{func_use}
"""

    def _rel_import(self, local_source: Optional[Path]) -> str:
        if not local_source:
            raise ValueError("local source must exist")

        path_to_viv = path_to_viv = str(
            local_source.resolve().absolute().parent.parent
        ).replace(str(Path.home()), "~")
        return (
            """__import__("sys").path.append(__import__("os")"""
            f""".path.expanduser("{path_to_viv}"))  # noqa"""
        )

    def _absolute_import(self, local_source: Optional[Path]) -> str:
        if not local_source:
            raise ValueError("local source must exist")

        path_to_viv = local_source.resolve().absolute().parent.parent
        return f"""__import__("sys").path.append("{path_to_viv}")  # noqa"""

    def frozen_import(
        self, path: str, local_source: Optional[Path], spec: List[str]
    ) -> str:
        if path == "abs":
            imports = self._absolute_import(local_source)
        elif path == "rel":
            imports = self._rel_import(local_source)
        else:
            imports = ""
        return f"""\
{imports}
{self.noqa(self._use_str(spec))}
"""

    def shim(
        self,
        path: str,
        local_source: Optional[Path],
        standalone: bool,
        spec: List[str],
        bin: str,
    ) -> str:
        if standalone:
            imports = self._standalone_func
        elif path == "abs":
            imports = self._absolute_import(local_source)
        elif path == "rel":
            imports = self._rel_import(local_source)
        else:
            imports = ""
        return f"""\
#!/usr/bin/env python
# AUTOGENERATED by viv (v{__version__})
# see `python3 <(curl -fsSL viv.dayl.in/viv.py) --help`

{imports}
import subprocess
import sys

if __name__ == "__main__":
    vivenv = {self.noqa(self._use_str(spec, standalone))}
    sys.exit(subprocess.run([vivenv / "bin" / "{bin}", *sys.argv[1:]]).returncode)
"""

    def update(
        self, src: Optional[Path], cli: Path, local_version: str, next_version: str
    ) -> str:
        return f"""
  Update source at {a.green}{src}{a.end}
  Symlink {a.bold}{src}{a.end} to {a.bold}{cli}{a.end}
  Version {a.bold}{local_version}{a.end} -> {a.bold}{next_version}{a.end}

"""

    def install(self, src: Path, cli: Path) -> str:
        return f"""
  Install viv.py to {a.green}{src}{a.end}
  Symlink {a.bold}{src}{a.end} to {a.bold}{cli}{a.end}

"""

    def show(
        self, cli: Optional[Path | str], running: Path, local: Optional[Path | str]
    ) -> str:
        return (
            "\n".join(
                f"  {a.bold}{k}{a.end}: {v}"
                for k, v in (
                    ("Version", __version__),
                    ("CLI", cli),
                    ("Running Source", running),
                    ("Local Source", local),
                )
            )
            + "\n"
        )


t = Template()


# TODO: convert the below functions into a proper file/stream logging interface
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
        a.subprocess(command, p.stdout)

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


@dataclass
class Meta:
    name: str
    id: str
    spec: List[str]
    files: List[str]
    exe: str
    created: str = ""
    accessed: str = ""

    @classmethod
    def load(cls, name: str) -> "Meta":
        if not (c.venvcache / name / "vivmeta.json").exists():
            warn(f"possibly corrupted vivenv: {name}")
            # add empty values for corrupted vivenvs so it will still load
            return cls(name=name, spec=[""], files=[""], exe="", id="")
        else:
            meta = json.loads((c.venvcache / name / "vivmeta.json").read_text())

        return cls(**meta)

    def write(self, p: Path | None = None) -> None:
        if not p:
            p = (c.venvcache) / self.name / "vivmeta.json"

        p.write_text(json.dumps(self.__dict__))

    def addfile(self, f: Path) -> None:
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
    ) -> None:
        self.loaded = False
        spec = self._validate_spec(spec)
        id = id if id else get_hash(spec, track_exe)

        self.name = name if name else id
        self.path = path if path else c.venvcache / self.name

        if not metadata:
            if self.name in (d.name for d in c.venvcache.iterdir()):
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

    def _validate_spec(self, spec: List[str]) -> List[str]:
        """ensure spec is at least of sequence of strings

        Args:
            spec: sequence of package specifications
        """
        if not set(map(type, spec)) == {str}:
            error("unexepected input in package spec")
            error(f"check your packages definitions: {spec}", code=1)

        return sorted(spec)

    def create(self, quiet: bool = False) -> None:
        if not quiet:
            echo(f"new unique vivenv -> {self.name}")
        with Spinner("creating vivenv"):
            venv.create(self.path, with_pip=True, clear=True, symlinks=True)

            # add config to ignore pip version
            (self.path / "pip.conf").write_text(
                "[global]\ndisable-pip-version-check = true"
            )

        self.meta.created = str(datetime.today())

    def install_pkgs(self) -> None:
        cmd: List[str] = [
            str(self.path / "bin" / "pip"),
            "install",
            "--force-reinstall",
        ] + self.meta.spec

        run(
            cmd,
            spinmsg="installing packages in vivenv",
            clean_up_path=self.path,
            verbose=bool(os.getenv("VIV_VERBOSE")),
        )

    def touch(self) -> None:
        self.meta.accessed = str(datetime.today())

    def show(self) -> None:
        _id = (
            self.meta.id[:8]
            if self.meta.id == self.name
            else (self.name[:5] + "..." if len(self.name) > 8 else self.name)
        )

        sys.stdout.write(
            f"""{a.bold}{a.cyan}{_id}{a.end} """
            f"""{a.style(", ".join(self.meta.spec),'dim')}\n"""
        )

    def _tree_leaves(self, items: List[str], indent: str = "") -> str:
        tree_chars = ["├"] * (len(items) - 1) + ["╰"]
        return "\n".join(
            (f"{indent}{a.yellow}{c}─{a.end} {i}" for c, i in zip(tree_chars, items))
        )

    def tree(self) -> None:
        _id = self.meta.id if self.meta.id == self.name else self.name
        # TODO: generarlize and loop this or make a template..
        items = [
            f"{a.magenta}{k}{a.end}: {v}"
            for k, v in {
                **{
                    "spec": ", ".join(self.meta.spec),
                    "created": self.meta.created,
                    "accessed": self.meta.accessed,
                },
                **({"exe": self.meta.exe} if self.meta.exe != "N/A" else {}),
                **({"files": ""} if self.meta.files else {}),
            }.items()
        ]
        rows = [f"\n{a.bold}{a.cyan}{_id}{a.end}", self._tree_leaves(items)]
        if self.meta.files:
            rows += (self._tree_leaves(self.meta.files, indent="   "),)

        sys.stdout.write("\n".join(rows) + "\n")


def get_caller_path() -> Path:
    """get callers callers file path"""
    # viv.py is fist in stack since function is used in `viv.use()`
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

    vivenv = ViVenv(list(packages), track_exe=track_exe, name=name)
    if not vivenv.loaded or os.getenv("VIV_FORCE"):
        vivenv.create()
        vivenv.install_pkgs()

    vivenv.meta.addfile(get_caller_path())
    vivenv.meta.write()

    modify_sys_path(vivenv.path)
    return vivenv.path


def modify_sys_path(new_path: Path) -> None:
    sys.path = [p for p in sys.path if p is not site.USER_SITE]
    site.addsitedir(str(*(new_path / "lib").glob("python*/site-packages")))


def get_venvs() -> Dict[str, ViVenv]:
    vivenvs = {}
    for p in c.venvcache.iterdir():
        vivenv = ViVenv.load(p.name)
        vivenvs[vivenv.name] = vivenv
    return vivenvs


def combined_spec(reqs: List[str], requirements: Path) -> List[str]:
    if requirements:
        with requirements.open("r") as f:
            reqs += f.readlines()
    return reqs


def resolve_deps(args: Namespace) -> List[str]:
    spec = combined_spec(args.reqs, args.requirements)

    cmd = [
        "pip",
        "install",
        "--dry-run",
        "--quiet",
        "--ignore-installed",
        "--report",
        "-",
    ] + spec

    report = json.loads(run(cmd, check_output=True, spinmsg="resolving depedencies"))
    resolved_spec = [
        f"{pkg['metadata']['name']}=={pkg['metadata']['version']}"
        for pkg in report["install"]
    ]

    return resolved_spec


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


class Viv:
    def __init__(self) -> None:
        self.vivenvs = get_venvs()
        self._get_sources()
        self.name = "viv" if self.local else "python3 <(curl -fsSL viv.dayl.in/viv.py)"

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

    def _match_vivenv(self, name_id: str) -> ViVenv:  # type: ignore[return]
        matches: List[ViVenv] = []
        for k, v in self.vivenvs.items():
            if name_id == k or v.name == name_id:
                matches.append(v)
            elif k.startswith(name_id) or (
                v.meta.id.startswith(name_id) and v.meta.id == v.name
            ):
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

        spec = resolve_deps(args)
        if args.keep:
            # re-create env again since path's are hard-coded
            vivenv = ViVenv(spec)

            if not vivenv.loaded or os.getenv("VIV_FORCE"):
                vivenv.create()
                vivenv.install_pkgs()
                vivenv.meta.write()
            else:
                echo("re-using existing vivenv")

            vivenv.touch()
            vivenv.meta.write()

        echo("see below for import statements\n")

        if args.standalone:
            sys.stdout.write(t.standalone(spec))
            return

        if args.path and not self.local_source:
            error("No local viv found to import from", code=1)

        sys.stdout.write(t.frozen_import(args.path, self.local_source, spec))

    def list(self, args: Namespace) -> None:
        """list all vivenvs"""

        if args.quiet:
            sys.stdout.write("\n".join(self.vivenvs) + "\n")
        elif len(self.vivenvs) == 0:
            echo("no vivenvs setup")
        elif args.full:
            for _, vivenv in self.vivenvs.items():
                vivenv.tree()
        elif args.json:
            sys.stdout.write(
                json.dumps({k: v.meta.__dict__ for k, v in self.vivenvs.items()})
            )
        else:
            for _, vivenv in self.vivenvs.items():
                vivenv.show()

    def exe(self, args: Namespace) -> None:
        """\
        run binary/script in existing vivenv

        examples:
            viv exe <vivenv> pip -- list
            viv exe <vivenv> python -- script.py
        """

        vivenv = self._match_vivenv(args.vivenv)
        bin = vivenv.path / "bin" / args.cmd

        if not bin.exists():
            error(f"{args.cmd} does not exist in {vivenv.name}", code=1)

        cmd = [bin, *args.rest]

        run(cmd, verbose=True)

    def info(self, args: Namespace) -> None:
        """get metadata about a vivenv"""
        vivenv = self._match_vivenv(args.vivenv)
        metadata_file = vivenv.path / "vivmeta.json"

        if not metadata_file.is_file():
            error(f"Unable to find metadata for vivenv: {args.vivenv}", code=1)
        if args.json:
            sys.stdout.write(json.dumps(vivenv.meta.__dict__))
        else:
            vivenv.tree()

    def _install_local_src(self, sha256: str, src: Path, cli: Path) -> None:
        echo("updating local source copy of viv")
        shutil.copy(c.srccache / f"{sha256}.py", src)
        make_executable(src)
        echo("symlinking cli")

        if cli.is_file():
            echo(f"Existing file at {a.style(str(cli),'bold')}")
            if confirm("Would you like to overwrite it?"):
                cli.unlink()
                cli.symlink_to(src)
        else:
            cli.symlink_to(src)

        echo("Remember to include the following line in your shell rc file:")
        sys.stderr.write(
            '  export PYTHONPATH="$PYTHONPATH:$HOME/'
            f'{src.relative_to(Path.home()).parent}"\n'
        )

    def _get_new_version(self, ref: str) -> Tuple[str, str]:
        sys.path.append(str(c.srccache))
        return (sha256 := fetch_source(ref)), __import__(sha256).__version__

    def manage(self, args: Namespace) -> None:
        """manage viv itself"""

        if args.subcmd == "show":
            if args.pythonpath:
                if self.local and self.local_source:
                    sys.stdout.write(str(self.local_source.parent) + "\n")
                else:
                    error("expected to find a local installation", code=1)
            else:
                echo("Current:")
                sys.stderr.write(
                    t.show(
                        cli=shutil.which("viv"),
                        running=self.running_source,
                        local=self.local_source,
                    )
                )

        elif args.subcmd == "update":
            sha256, next_version = self._get_new_version(args.ref)

            if self.local_version == next_version:
                echo(f"no change between {args.ref} and local version")
                sys.exit(0)

            if confirm(
                "Would you like to perform the above installation steps?",
                t.update(self.local_source, args.cli, self.local_version, next_version),
            ):
                self._install_local_src(
                    sha256,
                    Path(
                        args.src if not self.local_source else self.local_source,
                    ),
                    args.cli,
                )

        elif args.subcmd == "install":
            sha256, downloaded_version = self._get_new_version(args.ref)

            echo(f"Downloaded version: {downloaded_version}")

            # TODO: see if file is actually where
            # we are about to install and give more instructions

            if confirm(
                "Would you like to perform the above installation steps?",
                t.install(args.src, args.cli),
            ):
                self._install_local_src(sha256, args.src, args.cli)

        elif args.subcmd == "purge":
            to_remove = []
            if c._cache.is_dir():
                to_remove.append(c._cache)
            if args.src.is_file():
                to_remove.append(
                    args.src.parent if args.src == c.srcdefault else args.src
                )
            if self.local_source and self.local_source.is_file():
                if self.local_source.parent.name == "viv":
                    to_remove.append(self.local_source.parent)
                else:
                    to_remove.append(self.local_source)

            if args.cli.is_file():
                to_remove.append(args.cli)

            to_remove = list(set(to_remove))
            if confirm(
                "Remove the above files/directories?",
                "\n".join(f"  - {a.red}{p}{a.end}" for p in to_remove) + "\n",
            ):
                for p in to_remove:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()

                echo(
                    "to re-install use: "
                    "`python3 <(curl -fsSL viv.dayl.in/viv.py) manage install`"
                )

    def _pick_bin(self, args: Namespace) -> Tuple[str, str]:
        default = re.split(r"[=><~!*]+", args.reqs[0])[0]
        return default, (default if not args.bin else args.bin)

    def shim(self, args: Namespace) -> None:
        """\
        generate viv-powered cli apps

        examples:
          viv shim black
          viv shim yartsu -o ~/bin/yartsu --standalone
        """
        default_bin, bin = self._pick_bin(args)
        output = (
            c.binparent / default_bin if not args.output else args.output.absolute()
        )

        if output.is_file():
            error(f"{output} already exists...exiting", code=1)

        if args.freeze:
            spec = resolve_deps(args)
        else:
            spec = combined_spec(args.reqs, args.requirements)

        if confirm(
            f"Write shim for {a.style(bin,'bold')} to {a.style(output,'green')}?"
        ):
            with output.open("w") as f:
                f.write(
                    t.shim(args.path, self.local_source, args.standalone, spec, bin)
                )

            make_executable(output)

    def run(self, args: Namespace) -> None:
        """\
        run an app with an on-demand venv

        examples:
          viv r pycowsay -- "viv isn't venv\!"
          viv r rich -b python -- -m rich
        """

        _, bin = self._pick_bin(args)
        spec = combined_spec(args.reqs, args.requirements)
        vivenv = ViVenv(spec)

        # TODO: respect a VIV_RUN_MODE env variable as the same as keep i.e.
        # ephemeral (default), semi-ephemeral (persist inside /tmp), or
        # persist (use c.cache)

        if not vivenv.loaded or os.getenv("VIV_FORCE"):
            if not args.keep:
                with tempfile.TemporaryDirectory(prefix="viv-") as tmpdir:
                    vivenv.path = Path(tmpdir)
                    vivenv.create()
                    vivenv.install_pkgs()
                    sys.exit(
                        subprocess.run(
                            [vivenv.path / "bin" / bin, *args.rest]
                        ).returncode
                    )
            else:
                vivenv.create()
                vivenv.install_pkgs()

        vivenv.touch()
        vivenv.meta.write()

        sys.exit(subprocess.run([vivenv.path / "bin" / bin, *args.rest]).returncode)


class Arg:
    def __init__(self, *args: str, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


class Cli:
    args = {
        ("list",): [
            Arg(
                "-f",
                "--full",
                help="show full metadata for vivenvs",
                action="store_true",
            ),
            Arg(
                "-q",
                "--quiet",
                help="suppress non-essential output",
                action="store_true",
            ),
        ],
        ("shim",): [
            Arg(
                "-f",
                "--freeze",
                help="freeze/resolve all dependencies",
                action="store_true",
            ),
            Arg(
                "-o",
                "--output",
                help="path/to/output file",
                type=Path,
                metavar="<path>",
            ),
        ],
        ("remove",): [Arg("vivenv", help="name/hash of vivenv", nargs="*")],
        ("exe", "info"): [Arg("vivenv", help="name/hash of vivenv")],
        ("list", "info"): [
            Arg(
                "--json",
                help="name:metadata json for vivenvs ",
                action="store_true",
                default=False,
            )
        ],
        ("freeze", "shim"): [
            Arg(
                "-p",
                "--path",
                help="generate line to add viv to sys.path",
                choices=["abs", "rel"],
            ),
            Arg(
                "-s",
                "--standalone",
                help="generate standalone activation function",
                action="store_true",
            ),
        ],
        ("run", "freeze", "shim"): [
            Arg(
                "-k",
                "--keep",
                help="preserve environment",
                action="store_true",
            ),
            Arg("reqs", help="requirements specifiers", nargs="*"),
            Arg(
                "-r",
                "--requirements",
                help="path/to/requirements.txt file",
                metavar="<path>",
            ),
        ],
        ("run", "shim"): [
            Arg("-b", "--bin", help="console_script/script to invoke", metavar="<bin>"),
        ],
        ("manage|purge", "manage|update", "manage|install"): [
            Arg(
                "-r",
                "--ref",
                help="git reference (branch/tag/commit)",
                default="latest",
                metavar="<ref>",
            ),
            Arg(
                "-s",
                "--src",
                help="path/to/source_file",
                default=c.srcdefault,
                metavar="<src>",
            ),
            Arg(
                "-c",
                "--cli",
                help="path/to/cli (symlink to src)",
                default=Path.home() / ".local" / "bin" / "viv",
                metavar="<cli>",
            ),
        ],
        "manage|show": [
            Arg(
                "-p",
                "--pythonpath",
                help="show the path/to/install",
                action="store_true",
            )
        ],
        ("exe"): [
            Arg(
                "cmd",
                help="command to to execute",
            )
        ],
    }
    (
        cmds := dict.fromkeys(
            (
                "list",
                "shim",
                "run",
                "exe",
                "remove",
                "freeze",
                "info",
                "manage",
            )
        )
    ).update(
        {
            "manage": {
                subcmd: {"help": help, "aliases": [subcmd[0]]}
                for subcmd, help in (
                    ("show", "show current installation"),
                    ("install", "install fresh viv"),
                    ("update", "update viv version"),
                    ("purge", "remove traces of viv"),
                )
            }
        }
    )

    def __init__(self, viv: Viv) -> None:
        self.viv = viv
        self.parser = ArgumentParser(prog=viv.name, description=t.description)
        self._cmd_arg_group_map()
        self._make_parsers()
        self._add_args()

    def _cmd_arg_group_map(self) -> None:
        self.cmd_arg_group_map: Dict[str, List[Sequence[str] | str]] = {}
        for grp in self.args:
            if isinstance(grp, str):
                self.cmd_arg_group_map.setdefault(grp, []).append(grp)
            else:
                for cmd in grp:
                    self.cmd_arg_group_map.setdefault(cmd, []).append(grp)

    def _make_parsers(self) -> None:
        self.parsers = {**{grp: ArgumentParser(add_help=False) for grp in self.args}}

    def _add_args(self) -> None:
        for grp, args in self.args.items():
            for arg in args:
                self.parsers[grp].add_argument(*arg.args, **arg.kwargs)

    def _validate_args(self, args: Namespace) -> None:
        if args.func.__name__ in ("freeze", "shim", "run"):
            if not args.reqs:
                error("must specify a requirement", code=1)
        if args.func.__name__ in ("freeze", "shim"):
            if not self.viv.local_source and not (args.standalone or args.path):
                warn(
                    "failed to find local copy of `viv` "
                    "make sure to add it to your PYTHONPATH "
                    "or consider using --path/--standalone"
                )

            if args.path and not self.viv.local_source:
                error("No local viv found to import from", code=1)

            if args.path and args.standalone:
                error("-p/--path and -s/--standalone are mutually exclusive", code=1)

        if args.func.__name__ == "manage":
            if args.subcmd == "install" and self.viv.local_source:
                error(f"found existing viv installation at {self.viv.local_source}")
                echo(
                    "use "
                    + a.style("viv manage update", "bold")
                    + " to modify current installation.",
                    style="red",
                )
                sys.exit(1)
            if args.subcmd == "update":
                if not self.viv.local_source:
                    error(
                        a.style("viv manage update", "bold")
                        + " should be used with an exisiting installation",
                        1,
                    )

                if self.viv.git:
                    error(
                        a.style("viv manage update", "bold")
                        + " shouldn't be used with a git-based installation",
                        1,
                    )

    def _get_subcmd_parser(
        self,
        subparsers: _SubParsersAction[ArgumentParser],
        name: str,
        attr: Optional[str] = None,
        **kwargs: Any,
    ) -> ArgumentParser:
        # override for remove
        if name == "remove":
            aliases = ["rm"]
        else:
            aliases = kwargs.pop("aliases", [name[0]])

        cmd = getattr(self.viv, attr if attr else name)
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
                    title="subcommand", metavar="<sub-cmd>", required=True
                )
                for subcmd, kwargs in subcmds.items():
                    subcmd_cmd_p.add_parser(
                        subcmd,
                        parents=[
                            self.parsers[k]
                            for k in self.cmd_arg_group_map[f"{cmd}|{subcmd}"]
                        ],
                        **kwargs,
                    ).set_defaults(func=getattr(self.viv, cmd), subcmd=subcmd)

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
        else:
            args = self.parser.parse_args()
            args.rest = []

        self._validate_args(args)
        args.func(
            args,
        )


def main() -> None:
    viv = Viv()
    Cli(viv).run()


if __name__ == "__main__":
    main()
