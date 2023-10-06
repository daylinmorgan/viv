# Usage

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
