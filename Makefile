VERSION ?= $(shell git describe --tags --always --dirty=-dev | sed 's/^v//g')
PREFIX ?= ~/bin
## lint | run pre-commit hooks
lint:
	pdm run pre-commit run --all || pdm run pre-commit run --all
## types | run mypy
types:
	mypy src/viv

## bump-version | update version and tag commit
bump-version:
	@echo "bumping to version => $(VERSION)"
	@sed -i 's/__version__ = ".*"/__version__ = "$(VERSION)"/g' src/viv/viv.py
	@git add src/viv/viv.py && git commit -m "chore: bump version"
	@git tag v$(VERSION)

## env | generate environment
env:
	pdm install

## install | symlink to $PREFIX
install:
	ln -sf $(shell pwd)/src/viv/viv.py $(PREFIX)/viv

## uninstall | delete $(PREFIX)/viv
uninstall:
	rm $(PREFIX)/viv

## docs | generate usage examples
docs: docs/demo.gif docs/freeze.gif

docs/%.gif: docs/%.tape
	viv rm $$(viv l -q)
	vhs < $<

EXAMPLES = cli.py sys_path.py exe_specific.py frozen_import.py named_env.py scrape.py
generate-example-vivens:
	for f in $(EXAMPLES); \
		do python examples/$$f; done

.PHONY: env lint install uninstall \
	bump-version types docs generate-example-vivens

USAGE={a.bold}==>{a.cyan} viv isn't venv{a.end}\n\ttasks:
-include .task.mk
$(if $(filter help,$(MAKECMDGOALS)),$(if $(wildcard .task.mk),,.task.mk: ; curl -fsSL https://raw.githubusercontent.com/daylinmorgan/task.mk/v22.9.28/task.mk -o .task.mk))
