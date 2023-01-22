VERSION ?= $(shell git describe --tags --always --dirty=-dev | sed 's/^v//g')
PREFIX ?= ~/bin
lint: ## run pre-commit hooks
	pdm run pre-commit run --all || pdm run pre-commit run --all
types: ## run mypy
	mypy src/viv

bump-version: ## update version and tag commit
	@echo "bumping to version => $(VERSION)"
	@sed -i 's/__version__ = ".*"/__version__ = "$(VERSION)"/g' src/viv/viv.py
	@git add src/viv/viv.py && git commit -m "chore: bump version"
	@git tag v$(VERSION)

env: ## generate environment
	pdm install

install: ## symlink to $PREFIX
	ln -sf $(shell pwd)/src/viv/viv.py $(PREFIX)/viv

uninstall: ## delete $(PREFIX)/viv
	rm $(PREFIX)/viv

docs: docs/demo.gif docs/freeze.gif ## generate usage examples

docs/%.gif: docs/%.tape
	viv rm $$(viv l -q)
	vhs < $<

EXAMPLES = cli.py sys_path.py exe_specific.py frozen_import.py named_env.py scrape.py
generate-example-vivens: ##
	for f in $(EXAMPLES); \
		do python examples/$$f; done

-include .task.cfg.mk .task.mk
$(if $(filter help,$(MAKECMDGOALS)),$(if $(wildcard .task.mk),,.task.mk: ; curl -fsSL https://raw.githubusercontent.com/daylinmorgan/task.mk/v23.1.1/task.mk -o .task.mk))
