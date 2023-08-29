<!-- badges -->
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![PYPI][pypi-shield]][pypi-url]
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com)
[![Conda][conda-shield]][conda-url]

<div align="center">
  <a href="https://github.com/daylinmorgan/viv">
    <img src="https://raw.githubusercontent.com/daylinmorgan/viv/main/assets/logo.svg" alt="Logo" width=500 >
  </a>
  <p align="center">
  <h1> viv isn't venv </h1>
  </p>
  <div align="center">
    <img
      src="https://raw.githubusercontent.com/daylinmorgan/viv/main/assets/viv-help.svg"
      alt="cli screenshot"
      width="500"
      >
  </div>
  <p align="center">
    <a href="https://viv.dayl.in">Documentation</a>
  </p>
</div>

Try before you buy!
```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) run pycowsay -- "viv isn't venv\!"
```
---

`Viv` is a standalone dependency-free `venv` creator [^1].
`Viv` helps you ignore silly things like managing temporary or rarely used virtual environments,
while still unleashing the full power of python scripting with it's entire ecosystem at your disposal.

`Viv`'s uncompromising insistence on portability means that it will always:

1. only use the standard library
2. never exceed a single script.

For that reason any usage of the `cli` can be accomplished using a remote copy as seen in the below install command.

## Setup

Run the below command to install `viv`.

```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) manage install
```

To access `viv` from within scripts you should add it's location to your `PYTHONPATH`.
By default `viv` will be installed to `$XDG_DATA_HOME/viv` or `~/.local/share/viv` you can customize this with `--src`.

```sh
export PYTHONPATH="$PYTHONPATH:$HOME/.local/share/viv"
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
viv cache remove $(viv list -q)
```

To remove `viv` all together you can use the included `purge` command:

```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) manage purge
```
## Equivalent commands from alternatives

### [pip-run](https://github.com/jaraco/pip-run)


```sh
pip-run cowsay -- -m cowsay "moove over, pip-run"
python3 <(curl -fsSL viv.dayl.in/viv.py) run cowsay -- "moove over, pip-run"
```

```sh
python -m pip-run requests -- -c "import requests; print(requests.get('https://pypi.org/project/pip-run').status_code)"
python -m viv requests -b python -- -c "import requests; print(requests.get('https://pypi.org/project/viv').status_code)"
```

### [pipx](https://github.com/pypa/pipx/)

```sh
pipx install pycowsay
viv shim pycowsay
```

```sh
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
python3 <(curl -fsSL viv.dayl.in/viv.py) run \
  -s https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```

## Bonus: use `viv` with just standalone snippet (37LOC)

`--standalone` will auto-generate a mini function version of `viv` to accomplish the same basic task as using a local copy of `viv`.
After generating this standalone `shim` you can freely use this script across unix machines which have `python>3.8`.
See [examples/black](https://github.com/daylinmorgan/viv/blob/dev/examples/black) for output of below command.

`viv freeze` also supports `--standalone`

```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) shim black -o ./black --standalone --freeze
```


[^1]: You do need to have `pip` but surely you have `pip` already.

[conda-shield]: https://img.shields.io/conda/vn/conda-forge/viv
[conda-url]: https://anaconda.org/conda-forge/viv
[pypi-shield]: https://img.shields.io/pypi/v/viv
[pypi-url]: https://pypi.org/project/viv
[stars-shield]: https://img.shields.io/github/stars/daylinmorgan/viv.svg
[stars-url]: https://github.com/daylinmorgan/viv/stargazers
[issues-shield]: https://img.shields.io/github/issues/daylinmorgan/viv.svg
[issues-url]: https://github.com/daylinmorgan/viv/issues
[license-shield]: https://img.shields.io/github/license/daylinmorgan/viv.svg
[license-url]: https://github.com/daylinmorgan/viv/blob/main/LICENSE
