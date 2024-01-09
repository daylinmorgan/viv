# Configuration

## Environment Variables 

`VIV_RUN_MODE`
: **ephemeral** (default): 
  : `viv run` will generate a temporary directory that is removed following execution
: **semi-ephemeral**
  : `viv run` will set the `VIV_CACHE` directory to `$TEMPDIR/viv-ephemeral-cache-$USER`
: persist
  : `viv run` will always use the standard `VIV_CACHE` which maximizes reusable vivenvs

`VIV_CACHE`
: Path to use for vivenv cache by default `$XDG_CACHE_HOME/viv` or `$HOME/.cache/viv`

`VIV_LOG_PATH`
: Path to use for log file by default `$XDG_DATA_HOME/viv/viv.log` or `$HOME/.local/share/viv/viv.log`

`VIV_BIN_DIR`
: Path to use for shims by default `$HOME/.local/bin`

`VIV_NO_SETUPTOOLS`
: Don't add setuptools to generated vivenvs.
: Many legacy packages expect setuptools to be available
  and don't appropriately declare it as a dependency.
  To minimize frustration `setuptools` is added to every dependency
  list.

`VIV_FORCE`
: Remove existence check and recreate vivenv

`VIV_SPEC`
: Space separated list of dependencies in addition to those in script

`VIV_VERBOSE`
: Show `pip` output in real time

`VIV_DEBUG`
: Set log level to `DEBUG`

`FORCE_COLOR`
: Force output to use ANSI escape codes

`NO_COLOR`
: Remove all ANSI escape codes from output
