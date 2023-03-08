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

venv: ## generate environment
	pdm install

install: ## symlink to $PREFIX
	ln -sf $(shell pwd)/src/viv/viv.py $(PREFIX)/viv

uninstall: ## delete $(PREFIX)/viv
	rm $(PREFIX)/viv

TAPES = demo freeze list-info-remove
GIFS := $(foreach n, $(TAPES), docs/$(n).gif)
docs: $(GIFS) ## generate usage examples

docs/%.gif: docs/%.tape
	viv rm $$(viv l -q)
	cd docs; vhs < $*.tape

clean: ## remove build artifacts
	rm -rf {build,dist}

EXAMPLES = cli.py sys_path.py exe_specific.py frozen_import.py named_env.py scrape.py
generate-example-vivens: ##
	for f in $(EXAMPLES); \
		do python examples/$$f; done

-include .task.cfg.mk
