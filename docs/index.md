---
layout: landing
cover: http://viv.dayl.in/_static/logo.svg
desciption: Viv isn't venv
---

# viv isn't venv

Try before you buy!
```sh
python3 <(curl -fsSL viv.dayl.in/viv.py) run pycowsay -- "viv isn't venv\!"
```

:::{container} buttons

  [Docs](/installation)
  [Github](https://github.com/daylinmorgan/viv)

:::


`Viv` is a standalone dependency-free `venv` creator (just needs python + pip).
`Viv` helps you ignore silly things like managing temporary or rarely used virtual environments,
while still unleashing the full power of python scripting with it's entire ecosystem at your disposal.

`Viv`'s uncompromising insistence on portability means that it will always,
only use the standard library and never exceed a single script.

Documentation is currently a WIP please see the [cli reference](./cli.md) and the [README](https://github.com/daylinmorgan/viv)

```{toctree}
:hidden:
:maxdepth: 2

installation.md
usage.md
configuration.md
vs-others.md
cli.md
```

