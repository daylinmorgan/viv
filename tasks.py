#!/usr/bin/env python3
# # https://github.com/daylinmorgan/swydd?tab=readme-ov-file#automagic-snippet
# fmt: off
if not (src := __import__("pathlib").Path(__file__).parent / "swydd/__init__.py").is_file(): # noqa
    try: __import__("swydd") # noqa
    except ImportError:
        import sys; from urllib.request import urlopen; from urllib.error import URLError # noqa
        try: r = urlopen("https://raw.githubusercontent.com/daylinmorgan/swydd/main/src/swydd/__init__.py") # noqa
        except URLError as e: sys.exit(f"error fetching swydd: {e}\n") # noqa
        src.parent.mkdir(exists_ok=True); src.write_text(r.read().decode("utf-8")); # noqa
# fmt: on

from pathlib import Path

import swydd as s


@s.task
def venv():
    """setup up pdm venv"""
    s.sh("pdm install")


@s.task
def dev():
    """symlink development version"""
    s.sh(f"mkdir -p {Path.home()}/.local/share/viv")
    s.sh(f"mkdir -p {Path.home()}/.local/bin")
    s.sh(
        f"""ln -sf {Path.cwd()}/src/viv/viv.py """
        f"""{Path.home()}/.local/share/viv/viv.py"""
    )
    s.sh(f"ln -sf {Path.home()}/.local/share/viv/viv.py {Path.home()}/.local/bin/viv")


@s.targets("assets/viv-help.svg")
def _():
    s.sh(
        "FORCE_COLOR=1 viv --help | "
        "yartsu -t 'viv --help' -w 70 -o assets/viv-help.svg",
        shell=True,
    )


@s.targets("examples/black")
@s.needs("src/viv/viv.py")
def _():
    s.sh("rm -f examples/black")
    s.sh("viv shim black -y -s -f -o examples/black")


@s.task
def clean():
    """clean build artifacts"""
    s.sh("rm -rf build dist")


@s.task
@s.option("names", "list of names (comma-seperated)")
def examples(names: str = "cli,sys_path,exe_specific,frozen_import,named_env,scrape"):
    """run examples to generate vivenvs"""
    name_list = names.split(",")
    for name in name_list:
        s.sh(f"python examples/{name}.py")


@s.task
def release():
    """generate new release"""
    s.sh("./scripts/release.py")


print(s.ctx._tasks.items())
for id_, task in s.ctx._tasks.items():
    print(task.name)
    print(task.targets)
    print(task.needs)
s.cli()
