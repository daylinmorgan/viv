#!/usr/bin/env python3

import os
from pathlib import Path

import nox

nox.options.reuse_existing_virtualenvs = True
os.environ.update({"PDM_IGNORE_SAVED_PYTHON": "1"})

def pdm_install(session,group):
    session.run_always("pdm", "install", "-G", group, external=True, silent=True)


@nox.session
def lint(session):
    pdm_install(session,"dev")
    session.run("pre-commit", "run")
    session.run("mypy", "src/")

@nox.session
def svgs(session):
    pdm_install(session, "docs")
    session.run("./scripts/generate-svgs.py", external=True)

@nox.session
def docs(session):
    pdm_install(session,"docs")
    if not Path('docs/svgs').is_dir():
        svgs(session)

    session.run("make","docs", external=True)
    if session.interactive:
        session.run("mkdocs","serve")
    else:
        session.run("mkdocs","build")


# @nox.session(
#     python=["3.8", "3.9", "3.10", "3.11"]
# )
# def test(session):
#     pdm_install(session,'test')
#     session.run('pytest')
#
