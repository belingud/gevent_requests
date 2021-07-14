#!/usr/bin/env bash
# activate python env
command -v pyenv && pyenv shell "$(cat .python-version)"
rm -rf dist build
# build package
python setup.py sdist build bdist_wheel
command -v twine || pip install twine
twine upload dist/*