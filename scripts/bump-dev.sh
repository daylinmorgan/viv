#!/usr/bin/env bash
TAG=$(git describe --tags --always --dirty=-dev)
VERSION="${TAG#v}"
if [ "$NO_VERIFY" ]; then
	echo 'post-commit hook skipped' 1>&2
	exit 0
fi
if [[ "$(git diff --name-only HEAD HEAD~1)" == *"src/viv/viv.py"* ]]; then
	sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/g" src/viv/viv.py
fi
