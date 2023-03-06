set -x
set -e
python setup.py sdist
twine upload dist/*
