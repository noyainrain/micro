#!/bin/sh

set -e

bump_version() {
    FILE="${1:?}"
    PATTERN="${2:?}"
    cp "$FILE" /tmp/version
    sed "s/$PATTERN/\1$VERSION\3/" /tmp/version > "$FILE"
    git add "$FILE"
}

FEATURE=${FEATURE:?}
VERSION=${VERSION:?}

# Merge feature (abort if there are no changes)
git checkout master
git fetch
git merge
git merge --no-ff --no-commit $FEATURE
[ -f .git/MERGE_HEAD ]

# Bump version
bump_version setup.py "^\( *version='\)\(.*\)\(',\)$"
bump_version client/package.json '^\( *"version": "\)\(.*\)\(",\)$'
bump_version boilerplate/requirements.txt "^\(.*micro.git@\)\(.*\)\(\)$"
(VERSION=$(echo $VERSION | cut -d . -f -2) bump_version \
    boilerplate/client/package.json '^\( *"@noyainrain\/micro": "\^\)\(.*\)\("\)$')

# Run checks
make check

# Publish
git commit
git tag $VERSION
git push origin master $VERSION

# Clean up
git branch -d $FEATURE
git push --delete origin $FEATURE
