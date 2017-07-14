#!/bin/bash

if [[ -z $1 ]] || [[ -z $2 ]]; then
    echo "usage: dev/setup.sh projectname scriptname"
    exit 1
fi

set -e

./kapow.py repl -r ungapatchka:$1 -r kapow:$2 \
    $(find . -name "*.py")

mv ungapatchka $1
mv kapow.py ${2}.py
find . -name '*.pyc' | xargs rm

# set up new git repo
rm -rf .git
git init . && git add . && git commit -m "first commit"
git tag -a -m 0.1.0 0.1.0

# reset and check version
python setup.py check_version


