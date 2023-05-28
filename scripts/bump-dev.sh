#!/usr/bin/env sh
TAG=$(git describe --tags --always --dirty=-dev --exclude 'latest')
VERSION="${TAG#v}"
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/g" src/viv/viv.py
git add src/viv/viv.py
