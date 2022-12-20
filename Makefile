VERSION ?= $(shell git describe --tags --always --dirty=-dev | sed 's/^v//g')
VENV_BIN = ./.venv/bin

lint:
	pre-commit run --all || pre-commit run --all

types:
	mypy src/

bump-version:
	@echo "bumping to version => $(VERSION)"
	@sed -i 's/__version__ = ".*"/__version__ = "$(VERSION)"/g' src/viv.py

env:
	python -m venv ./.venv --upgrade-deps
	$(VENV_BIN)/pip install pre-commit mypy
	$(VENV_BIN)/pre-commit install --install-hooks

install:
	ln -sf $(shell pwd)/src/viv.py ~/bin/viv

uninstall:
	rm ~/bin/viv

.PHONY: env lint install uninstall bump-version types
