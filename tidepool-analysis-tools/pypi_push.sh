rm dist/*
python setup.py sdist
echo "RUN: twine upload dist/{VERSION}.tar.gz"