# Vs Others

## Equivalent commands from alternatives

### [pip-run](https://github.com/jaraco/pip-run)


```sh
pip-run cowsay -- -m cowsay "moove over, pip-run"
python3 <(curl -fsSL viv.dayl.in/viv.py) run cowsay -- "moove over, pip-run"
```

```sh
python -m pip-run requests -- -c "import requests; print(requests.get('https://pypi.org/project/pip-run').status_code)"
python -m viv run requests -b python -- -c "import requests; print(requests.get('https://pypi.org/project/viv').status_code)"
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


