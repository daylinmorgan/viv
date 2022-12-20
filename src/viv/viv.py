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
from pathlib import Path
from typing import Dict, List, Tuple

__version__ = "22.12a2"


@dataclass
class Config:
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
                    sys.stdout.write("\r\033[K")  # move back then delete the line
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

    def __exit__(self, exc_type, exc_val, exc_traceback):
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
    bold: str = "\033[1m"
    dim: str = "\033[2m"
    underline: str = "\033[4m"
    red: str = "\033[1;31m"
    green: str = "\033[1;32m"
    yellow: str = "\033[1;33m"
    magenta: str = "\033[1;35m"
    cyan: str = "\033[1;36m"
    end: str = "\033[0m"

    def __post_init__(self):
        if os.getenv("NO_COLOR"):
            for attr in self.__dict__:
                setattr(self, attr, "")

    def style(self, txt: str, hue: str = "cyan") -> str:
        """style text with given hue
        Args:
            txt: text to stylize
            hue: color/style to apply to text
        Returns:
            ansi escape code stylized text
        """
        return f"{getattr(self,hue)}{txt}{getattr(self,'end')}"

    def tagline(self):
        """generate the viv tagline!"""
        return " ".join(
            (
                self.style(f, "magenta") + self.style(rest, "cyan")
                for f, rest in (("V", "iv"), ("i", "sn't"), ("v", "env!"))
            )
        )

    def subprocess(self, output):
        new_output = [f"{self.red}->{self.end} {line}" for line in output.splitlines()]

        sys.stdout.write("\n".join(new_output) + "\n")

    def _get_column_size(self, sizes, row):
        for i, length in enumerate(len(cell) for cell in row):
            if length > sizes[i]:
                sizes[i] = length
        return sizes

    def _make_row(self, row) -> str:

        return f"  {BOX['v']} " + f" {BOX['sep']} ".join(row) + f" {BOX['v']}"

    def table(self, rows, header_style="cyan") -> None:
        # TODO: make this function screen size aware...either with wrapping or cropping

        sizes = [0] * len(rows[0])
        for row in rows:
            sizes = self._get_column_size(sizes, row)

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
                    for row in rows[1:]
                ),
            )
        )
        sys.stdout.write(f"  {BOX['tl']}{BOX['h']*(sum(sizes)+5)}{BOX['tr']}\n")
        sys.stdout.write("\n".join(table_rows) + "\n")
        sys.stdout.write(f"  {BOX['bl']}{BOX['h']*(sum(sizes)+5)}{BOX['br']}\n")


a = Ansi()


def error(msg, code: int = 0):
    echo(f"{a.red}error:{a.end} {msg}", hue="red")
    if code:
        sys.exit(code)


def warn(msg):
    echo(f"{a.yellow}warn:{a.end} {msg}", hue="yellow")


def echo(msg: str, hue="magenta", newline=True) -> None:
    output = f"{a.cyan}Viv{a.end}{a.__dict__[hue]}::{a.end} {msg}"
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
        echo("see below for command output", hue="red")
        a.subprocess(p.stdout)

        if clean_up_path and clean_up_path.is_dir():
            shutil.rmtree(str(clean_up_path))

        sys.exit(p.returncode)

    elif check_output:
        return p.stdout

    else:
        return ""


def get_hash(package_spec: Tuple[str, ...] | List[str], track_exe: bool) -> str:
    pkg_hash = hashlib.sha256()
    pkg_hash.update(str(package_spec).encode())

    # generate unique venvs for unique python exe's
    if track_exe:
        pkg_hash.update(str(Path(sys.executable).resolve()).encode())

    return pkg_hash.hexdigest()


class ViVenv:
    # TODO: make method to generate venv from the info file?
    def __init__(
        self,
        spec: List[str],
        track_exe: bool = False,
        build_id: str | None = None,
        name: str = "",
        path: Path | None = None,
    ) -> None:
        self.spec = spec
        self.exe = str(Path(sys.executable).resolve()) if track_exe else "N/A"
        self.build_id = build_id if build_id else get_hash(spec, track_exe)
        self.name = name if name else self.build_id
        self.path = path if path else c.venvcache / self.name

    @classmethod
    def load(cls, name) -> "ViVenv":
        if not (c.venvcache / name / "viv-info.json").is_file():
            warn(f"possibly corrupted vivenv: {name}")
            return cls(name=name, spec=[""])
        else:
            with (c.venvcache / name / "viv-info.json").open("r") as f:
                venvconfig = json.load(f)

        vivenv = cls(
            name=name, spec=venvconfig["spec"], build_id=venvconfig["build_id"]
        )
        vivenv.exe = venvconfig["exe"]

        return vivenv

    def create(self) -> None:

        # TODO: make sure it doesn't exist already?
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
            spinmsg=f"installing packages in vivenv",
            clean_up_path=self.path,
            verbose=bool(os.getenv("VIV_VERBOSE")),
        )

    def dump_info(self, write=False):
        # TODO: include associated files in 'info'
        # means it needs to be loaded first
        info = {
            "created": str(datetime.today()),
            "build_id": self.build_id,
            "spec": self.spec,
            "exe": self.exe,
        }
        # save metadata to json file
        if write:
            with (self.path / "viv-info.json").open("w") as f:
                json.dump(info, f)
        else:
            info["spec"] = ";".join(self.spec)
            a.table((("key", "value"), *((k, v) for k, v in info.items())))


def activate(*packages: str, track_exe: bool = False, name: str = "") -> None:
    vivenv = ViVenv(validate_spec(packages), track_exe=track_exe, name=name)

    if vivenv.name not in [d.name for d in c.venvcache.iterdir()] or os.getenv(
        "VIV_FORCE"
    ):
        vivenv.create()
        vivenv.install_pkgs()
        vivenv.dump_info(write=True)

    modify_sys_path(vivenv.path)


def validate_spec(spec) -> List[str]:
    to_install: List[str] = []

    if set(map(type, spec)) == {str}:
        to_install.extend(pkg for pkg in spec)
    else:
        error("unexepected input in package spec")
        error(f"check your packages definitions: {spec}", code=1)

    return to_install


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
IMPORT_TEMPLATE = """__import__("viv").activate({spec})  # noqa"""


def spec_to_import(spec: List[str]) -> None:
    spec_str = ", ".join(f'"{pkg}"' for pkg in spec)
    sys.stdout.write(IMPORT_TEMPLATE.format(spec=spec_str) + "\n")


def generate_import(
    requirements: Path, reqs: List[str], vivenvs, include_path: bool
) -> None:
    # TODO: make compatible with Venv class for now just use the name /tmp/
    reqs_from_file = []

    if requirements:
        with requirements.open("r") as f:
            reqs_from_file = f.readlines()

    # refactor to make the below steps context dependent with tmpdir path
    with tempfile.TemporaryDirectory() as tmpdir:  #
        echo(f"using temporary vivenv: {tmpdir}")
        vivenv = ViVenv(reqs + reqs_from_file, track_exe=False, path=Path(tmpdir))

        vivenv.create()
        # populate the environment for now use custom cmd since using requirements file
        cmd = [
            vivenv.path / "bin" / "pip",
            "install",
            "--force-reinstall",
        ]
        if requirements:
            cmd += ["-r", requirements]
        if reqs:
            cmd += reqs

        run(cmd, spinmsg="resolving dependencies", clean_up_path=vivenv.path)

        # generate a frozen environment
        cmd = [vivenv.path / "bin" / "pip", "freeze"]
        output = run(cmd, check_output=True)

        echo("see below for import statements\n")
        if include_path:
            sys.stdout.write(
                SYS_PATH_TEMPLATE.format(
                    path_to_viv=Path(__file__).resolve().absolute().parent
                )
                + "\n"
            )

        spec_to_import(output.splitlines())


class CustomHelpFormatter(RawDescriptionHelpFormatter, HelpFormatter):
    """formatter to remove extra metavar on short opts"""

    def __init__(self, *args, **kwargs):
        super(CustomHelpFormatter, self).__init__(
            *args, max_help_position=40, width=90, **kwargs
        )

    def _format_action_invocation(self, action):
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string


class ArgumentParser(StdArgParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formatter_class = CustomHelpFormatter

    def error(self, message):
        error(message)
        echo("see below for help", hue="red")
        self.print_help()
        sys.exit(2)


description = f"""
usage: viv <sub-cmd> [-h]

{a.tagline()}

{a.style('create/activate a vivenv','underline')}
from command line:
  `{a.style("viv -h","bold")}`
within python script:
  {a.style('__import__("viv").activate("typer", "rich-click")','bold')}

commands:
  list (l)    list all viv vivenvs
  exe         run python/pip in vivenv
  remove (rm) remove a vivenv
  freeze (f)  create import statement from package spec
  info (i)    get metadata about a vivenv
"""


def cmd_desc(subcmd):
    return f"usage: viv {subcmd} [-h]"


class Viv:
    def __init__(self):
        self.vivenvs = get_venvs()

    def _match_vivenv(self, name_id: str) -> ViVenv:
        matches = []
        for k, v in self.vivenvs.items():
            if name_id == k or v.name == name_id:
                matches.append(v)
            elif k.startswith(name_id) or v.build_id.startswith(name_id):
                matches.append(v)
            elif v.name.startswith(name_id):
                matches.append(v)
        if not matches:
            error(f"no matches found for {name_id}", code=1)
        elif len(matches) > 1:
            echo(f"matches {','.join(matches)}", hue="red")
            error("too many matches maybe try a longer name?", code=1)
        else:
            return matches[0]

    def remove(self, args):
        """remove a vivenv"""

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

        generate_import(args.requirements, args.reqs, self.vivenvs, args.path)

    def _make_row(self, vivenv: ViVenv):
        name = vivenv.name if len(vivenv.name) <= 9 else f"{vivenv.name[:6]}..."
        return f" │ {name:<9} ┆ {vivenv.spec}"

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
                        ";".join(vivenv.spec),
                    )
                    for vivenv in self.vivenvs.values()
                ),
            )
            a.table(rows)

    def exe(self, args):
        """run python/pip in vivenv"""

        vivenv = self._match_vivenv(args.vivenv)
        # if args.vivenv not in self.vivenvs:
        # print(f"{args.vivenv}" not in self.vivenvs)

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

    def cli(self):

        parser = ArgumentParser(description=description, usage=SUPPRESS)
        parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"{a.bold}viv{a.end}, version {a.cyan}{__version__}{a.end}",
        )
        subparsers = parser.add_subparsers(
            metavar="<sub-cmd>", title="subcommands", help=SUPPRESS, required=True
        )

        p_vivenv_arg = ArgumentParser(add_help=False)
        p_vivenv_arg.add_argument("vivenv", help="name/hash of vivenv")

        p_list = subparsers.add_parser(
            "list",
            help=self.list.__doc__,
            aliases=["l"],
            description=cmd_desc("list"),
            usage=SUPPRESS,
        )
        p_list.add_argument(
            "-q", "--quiet", help="suppress non-essential output", action="store_true"
        )
        p_list.set_defaults(func=self.list)

        p_exe = subparsers.add_parser(
            "exe",
            help=self.exe.__doc__,
            usage=SUPPRESS,
            description=cmd_desc("exe"),
        )
        p_exe_sub = p_exe.add_subparsers(
            title="subcommand", metavar="<sub-cmd>", required=True
        )
        #
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

        p_remove = subparsers.add_parser(
            "remove",
            help=self.remove.__doc__,
            aliases=["rm"],
            usage=SUPPRESS,
            description=cmd_desc("remove"),
        )
        p_remove.add_argument("vivenv", help="name/hash of vivenv", nargs="*")
        p_remove.set_defaults(func=self.remove)

        p_freeze = subparsers.add_parser(
            "freeze",
            help=self.freeze.__doc__,
            aliases=["f"],
            usage=SUPPRESS,
            description=cmd_desc("freeze"),
        )
        p_freeze.add_argument(
            "-p",
            "--path",
            help="generate line to add viv to sys.path",
            action="store_true",
        )
        p_freeze.add_argument(
            "-r",
            "--requirements",
            help="path to requirements.txt file",
            metavar="<path-to-file>",
        )
        p_freeze.add_argument(
            "-k",
            "--keep",
            help="preserve environment",
            action="store_true",
        )
        p_freeze.add_argument("reqs", help="requirements specifiers", nargs="*")
        p_freeze.set_defaults(func=self.freeze)

        p_info = subparsers.add_parser(
            "info",
            help=self.info.__doc__,
            parents=[p_vivenv_arg],
            aliases=["i"],
            description=cmd_desc("info"),
            usage=SUPPRESS,
        )
        p_info.set_defaults(func=self.info)
        parser.set_defaults(quiet=False)

        args = parser.parse_args()

        args.func(args)


def main():
    viv = Viv()
    viv.cli()


if __name__ == "__main__":
    main()
