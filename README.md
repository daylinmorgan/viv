# Viv

<!-- PROJECT DEMO -->
<div align="center">
  <a href="https://github.com/daylinmorgan/viv">
    <img src="https://raw.githubusercontent.com/daylinmorgan/viv/main/docs/demo.gif" alt="Logo" width=600 >
  </a>
  <p align="center">
  viv isn't venv
  </p>
</div>
<br />

## Setup

Start by cloning the repo and symlinking the script for access to the CLI.
By default it will symlink `./src/viv/viv.py` to `~/bin/viv`.
You can set `PREFIX` to symlink to a different location.

```sh
git clone git@github.com:daylinmorgan/viv.git ~/.viv
cd ~/.viv
make install # or PREFIX=~/.local/bin make install
```

Place this directory on the python path in your rc file.

```sh
export PYTHONPATH="$PYTHONPATH:$HOME/.viv/src"
```

Then in any python script with external dependencies you can add this line.

```python
__import__("viv").activate("click")
```

## Usage

To remove all viv venvs:
```sh
viv remove $(viv list -q)
```

## Alternatives

- `pipx`
- `pip-run`
