tests/fixture
=============

Files under `tests/fixture` are used by `test_functional.py`.
`test_functional.py` runs sphinx.build with *fake* rr executable,
`fakecmd.py`.

If you want to run sphinx-build with the real environment, please follow
these steps:

 1. put `rr.war` under `tests/fixture`.
 2. run `make html` or something.
