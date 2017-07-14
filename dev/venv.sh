#!/bin/bash
# Usage: bin/bootstrap.sh [Options]

# Create a virtualenv, and install requirements to it.

# override the default python interpreter using
# `PYTHON=/path/to/python bin/bootstrap.sh`

if [[ -n $VIRTUAL_ENV ]]; then
    echo "You can't run this script inside an active virtualenv"
    exit 1
fi

set -e

abspath(){
    python -c "import os; print os.path.abspath(\"$1\")"
}

# defaults for options configurable from the command line
GREP_OPTIONS=--color=never
VENV=$(basename $(pwd))-env
PYTHON=$(which python)
PY_VERSION=$($PYTHON -c 'import sys; print "{}.{}.{}".format(*sys.version_info[:3])')
WHEELSTREET=/usr/local/share/python/wheels
REQFILE=requirements.txt

if [[ $1 == '-h' || $1 == '--help' ]]; then
    echo "Create a virtualenv and install all pipeline dependencies"
    echo "Options:"
    echo "--venv            - path of virtualenv [$VENV]"
    echo "--python          - path to the python interpreter [$PYTHON]"
    echo "--wheelstreet     - path to directory containing python wheels; wheel files will be"
    echo "                    in a subdirectory named according to the python interpreter version;"
    echo "                    uses WHEELSTREET if defined."
    echo "                    (a suggested alternative location is ~/wheelstreet) [$WHEELSTREET]"
    echo "--requirements    - a file listing python packages to install [$REQFILE]"
    exit 0
fi

while true; do
    case "$1" in
	--venv ) VENV="$2"; shift 2 ;;
	--python ) PYTHON="$2"; shift 2 ;;
	--wheelstreet ) WHEELSTREET=$(abspath "$2"); shift 2 ;;
	--requirements ) REQFILE="$2"; shift 2 ;;
	* ) break ;;
    esac
done

VENV_VER=1.11.6
WHEELHOUSE=

if [[ -n "$WHEELSTREET" && -d "$WHEELSTREET" ]]; then
    WHEELHOUSE=$WHEELSTREET/$PY_VERSION
    test -d $WHEELHOUSE || (echo "cannot access $WHEELHOUSE"; exit 1)
fi

mkdir -p src

# Create the virtualenv using a specified version of the virtualenv
# source. This also provides setuptools and pip.

check_version(){
    # usage: check_version module version-string
    "$PYTHON" <<EOF 2> /dev/null
import $1
from distutils.version import LooseVersion
assert LooseVersion($1.__version__) >= LooseVersion("$2")
EOF
}

# create virtualenv if necessary
VENV_URL="https://pypi.python.org/packages/source/v/virtualenv"
if [[ ! -f "${VENV:?}/bin/activate" ]]; then
    # if the system virtualenv is up to date, use it
    if check_version virtualenv $VENV_VER; then
	echo "using $(which virtualenv) (version $(virtualenv --version))"
    	virtualenv "$VENV"
    else
	echo "downloading virtualenv version $VENV_VER"
	if [[ ! -f src/virtualenv-${VENV_VER}/virtualenv.py ]]; then
	    mkdir -p src
	    (cd src && \
		wget -N ${VENV_URL}/virtualenv-${VENV_VER}.tar.gz && \
		tar -xf virtualenv-${VENV_VER}.tar.gz)
	fi
	"$PYTHON" src/virtualenv-${VENV_VER}/virtualenv.py "$VENV"
    fi
else
    echo "virtualenv $VENV already exists"
fi

if [[ ! -f "$REQFILE" ]]; then
    exit
fi

source $VENV/bin/activate

# install python packages from pipy or wheels
grep -v -E '^#|git+|^-e' $REQFILE | while read pkg; do
    if [[ -z $WHEELHOUSE ]]; then
	pip install $pkg
    else
	pip install --use-wheel --find-links=$WHEELHOUSE $pkg
    fi
done

# install packages from git repos if necessary
if [[ ! -z $(grep git+ $REQFILE | grep -v -E '^#') ]]; then
    pip install -r <(grep git+ $REQFILE | grep -v -E '^#')
else
    echo "no packages to install from git repositories"
fi

# correct any more shebang lines
# virtualenv --relocatable $VENV
