#FAKEROOT = fakeroot
PYTHON := venv/bin/python
PIP := venv/bin/pip
TWINE := twine

export PYTHONPATH := $(CURDIR)/sphinxcontrib

.PHONY: dist
dist: venv
	$(PYTHON) setup.py sdist

.PHONY: upload
upload: dist
	$(TWINE) upload dist/*

.PHONY: check
check: venv
	echo PYTHONPATH: $$PYTHONPATH
	$(PYTHON) -m pytest

.PHONY: clean
clean: venv
	$(PYTHON) setup.py clean

.PHONY: distclean
distclean: clean
	$(RM) -R build dist *.egg-info venv

venv:
	python3 -m venv venv
	$(PIP) install -r requirements.txt
