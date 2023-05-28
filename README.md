# viv

<div align="center">
  <a href="https://github.com/daylinmorgan/viv">
    <img src="https://raw.githubusercontent.com/daylinmorgan/viv/main/assets/logo.svg" alt="Logo" width=500 >
  </a>
  <p align="center">
  viv isn't venv
  </p>
</div>
<br />
---

`Viv` is a standalone dependency-free `venv` creator.

These `venvs` can be identified by name or by their specification.
In any case they will be re-used across scripts (and generated on-demand, if needed).

**Importantly**, `viv` will also remove your user site directory.
(view with: `python -m 'import site;print(site.USER_SITE)'`).

`Viv`'s uncompromising insistence on portability means that it will always (1) only use the standard library (2) never exceed a single script.

For that reason any usage of the `CLI` can be accomplished using a remote copy as seen in the below install command.

## Setup

Run the below command to install `viv`.

```sh
python3 <(curl -fsSL gh.dayl.in/viv/viv.py) manage install
```

To access `viv` from within scripts you should add it's location to your `PYTHONPATH`.
By default `viv` will be installed to `$XDG_DATA_HOME/viv` or `~/.local/share/viv` you can customize this with `--src`.

```sh
export PYTHONPATH="$PYTHONPATH:$HOME/.local/share/viv"
```

Advanced users may recognize that principally,
the module just needs to be recognized at run time
and the single script [`viv.py`](https://github.com/daylinmorgan/viv/blob/main/src/viv/viv.py) can be invoked directly for the CLI.
How you accomplish these options is ultimately up to you but the above instructions can get you started.

## Additional Features

An experimental feature of `viv` is generating shim's that leverage the principles of `viv`.
These shims would operate similar to `pipx` in which you can specify a command line app to "install".

*Note* that `--standalone` will auto-generate a code-golfed minified version of `viv` to accomplish the same basic task as using a local copy of `viv`.
After generating this a standalone `shim` you can freely use this script across unix machines which have `python>3.8`.
See [examples/black](https://github.com/daylinmorgan/viv/blob/dev/examples/black) for output of below command.

```sh
python3 <(curl -fsSL gh.dayl.in/viv/viv.py) shim black -o ./black --standalone --freeze
```

### Pypi (Not Recommended)

```sh
pip install viv
```

Why is this *not recommended*? Mainly, because `viv` is all about hacking your `sys.path`.
Placing it in it's own virtual environment or installing in a user site directory may complicate this endeavor.

## Usage

In any python script with external dependencies you can add this line,
to automate `vivenv` creation and installation of dependencies.

```python
__import__("viv").use("click")
```

To remove all `vivenvs` you can use the below command:

```sh
viv remove $(viv list -q)
```

To remove `viv` all together you can use the included `purge` command:

```sh
python3 <(curl -fsSL gh.dayl.in/viv/viv.py) manage purge
```

## Alternatives

### [pip-run](https://github.com/jaraco/pip-run)

```sh
pip-run (10.0.5)
├── autocommand (2.2.2)
├── jaraco-context (4.3.0)
├── jaraco-functools (3.6.0)
│   └── more-itertools (9.1.0)
├── jaraco-text (3.11.1)
│   ├── autocommand (2.2.2)
│   ├── inflect (6.0.2)
│   │   └── pydantic>=1.9.1 (1.10.5)
│   │       └── typing-extensions>=4.2.0 (4.5.0)
│   ├── jaraco-context>=4.1 (4.3.0)
│   ├── jaraco-functools (3.6.0)
│   │   └── more-itertools (9.1.0)
│   └── more-itertools (9.1.0)
├── more-itertools>=8.3 (9.1.0)
├── packaging (23.0)
├── path>=15.1 (16.6.0)
├── pip>=19.3 (23.0.1)
└── platformdirs (3.1.0)
```

### [pipx](https://github.com/pypa/pipx/)

```sh
pipx (1.1.0)
├── argcomplete>=1.9.4 (2.1.1)
├── packaging>=20.0 (23.0)
└── userpath>=1.6.0 (1.8.0)
    └── click (8.1.3)
```
