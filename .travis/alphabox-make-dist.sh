#!/bin/bash
: ${PYTHON=python}

set -e
if [[ ${TRAVIS} != "" ]]; then
    set -x
fi

set -x
SEAHUB_TESTSDIR=$(python -c "import os; print os.path.dirname(os.path.realpath('$0'))")
SEAHUB_SRCDIR=$(dirname "${SEAHUB_TESTSDIR}")

export PYTHONPATH="/usr/local/lib/python2.7/site-packages:/usr/lib/python2.7/site-packages:${SEAHUB_SRCDIR}/thirdpart:${PYTHONPATH}"
cd "$SEAHUB_SRCDIR"
set +x

function build_frontend() {
    git checkout -b alphabox-dist

    echo "Building frontend/src files ..."
    cd ./frontend && npm install && CI=false npm run build && cd ..

}

function make_dist() {
    echo "Making dist files ..."
    make dist
}

function commit_dist_files() {
  git add -u . && git add -A media/assets && git add -A static/scripts && git add -A frontend && git add -A locale
  git commit -m "[dist] npm run build && make dist"
}

function upload_files() {
    git fetch origin

    # for seahub-priv
    echo 'push to seahub priv'
    git remote add seahub-priv https://imwhatiam:${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/seafileltd/seahub-priv.git
    git push -f seahub-priv alphabox-dist

    # for seahub-extra
    echo 'push to seahub extra'
    git remote add seahub-extra https://imwhatiam:${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/seafileltd/seahub-extra.git

    git fetch seahub-extra 7.0:seahub-extra-7.0
    git fetch seahub-extra alphabox-7.0:seahub-extra-alphabox-dist

    git checkout seahub-extra-alphabox-dist
    git rebase seahub-extra-7.0
    git push -f seahub-extra seahub-extra-alphabox-dist:alphabox-dist
}

build_frontend
make_dist
commit_dist_files
upload_files
