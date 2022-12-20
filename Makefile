VERSION ?= $(shell git describe --tags --always --dirty=-dev | sed 's/^v//g')
PREFIX ?= ~/bin

lint:
	pdm run pre-commit run --all || pdm run pre-commit run --all

types:
	mypy src/

bump-version:
	@echo "bumping to version => $(VERSION)"
	@sed -i 's/__version__ = ".*"/__version__ = "$(VERSION)"/g' src/viv.py

env:
	pdm install

install:
	ln -sf $(shell pwd)/src/viv/viv.py $(PREFIX)/viv

uninstall:
	rm ~/bin/viv

.PHONY: env lint install uninstall bump-version types
