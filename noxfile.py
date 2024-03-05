#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

import nox

nox.options.sessions = ["lint", "typecheck"]
nox.options.reuse_existing_virtualenvs = True
os.environ.update({"PDM_IGNORE_SAVED_PYTHON": "1"})


def pdm_install(session, group):
    session.run_always("pdm", "install", "-G", group, external=True, silent=True)


@nox.session
def lint(session):
    pdm_install(session, "dev")
    session.run("pre-commit", "run")


@nox.session
def typecheck(session):
    pdm_install(session, "dev")
    session.run("mypy", "src/")


@nox.session
def svgs(session):
    pdm_install(session, "docs")
    session.run(
        "./scripts/generate-svgs.py", external=True, env={"FORCE_COLOR": "true"}
    )


@nox.session
def docs(session):
    pdm_install(session, "docs")
    Path("docs").mkdir(exist_ok=True)

    if not Path("docs/svgs").is_dir():
        svgs(session)

    shutil.copyfile("src/viv/viv.py", "docs/viv.py")
    if session.interactive:
        session.run("sphinx-autobuild", "docs", "site", "--port", "8787")
    else:
        session.run("sphinx-build", "docs", "site")


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
def test(session):
    pdm_install(session, "test")
    session.run("pytest", "tests/")
