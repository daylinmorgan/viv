# Installation

## Automated

Run the below command to install `viv`.

```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) manage install
```

To access `viv` from within scripts you should add its location to your `PYTHONPATH`.
By default `viv` will be installed to `$XDG_DATA_HOME/viv` or `~/.local/share/viv`,
and symlinked to `$XDG_BIN_HOME` or `~/.local/bin/.`
You can customize these locations at install with with `--src` and `--cli` respectively.

```sh
export PYTHONPATH="$PYTHONPATH:$HOME/.local/share/viv"
# or
export PYTHONPATH="$PYTHONPATH:$(viv manage show --pythonpath)"
```

:::{note}
You can install an older version by specifying  `--ref`
:::

## Manual

Viv is a single standalone script meaning all that's really necessary is
that it exists locally and is appropriately added to your path.
You can get the latest stable version from [here](https://viv.dayl.in/viv.py)
or from [github](https://github.com/daylinmorgan/viv/blob/latest/src/viv/viv.py).

Must be added to your `$PATH` for use as a CLI app and `$PYTHONPATH` for uses as a python module.

## Never

Viv is a standalone script accessible at `https://viv.dayl.in/viv.py`
meaning it's not strictly necessary you every actually install it.
Every instance of the `viv` CLI can be seamlessly replaced with `python3 <(curl -fsSL viv.dayl.in/viv.py)`.

## PyPI Options (Not Recommended)

Why is this *not recommended?*
Mainly because `viv` is all about hacking your `sys.path`.
Placing it in its own virtual environment
or installing in a user site directory may complicate this endeavor.

```sh
pip install viv
# or
pipx install viv
```
 
*Note*: If installed by `pipx`, it should still be possible to
use `viv` as a module by adding it to the `$PYTHONPATH`.
See above for more info.
