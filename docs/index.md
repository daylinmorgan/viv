---
hide-toc: true
---

# viv isn't venv

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

Documentation is currently a WIP please see the [cli reference](./cli.md) and the [README](https://github.com/daylinmorgan/viv)

```{toctree}
:hidden:

usage.md
cli.md
```


