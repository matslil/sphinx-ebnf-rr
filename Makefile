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
check: venv rr.war
	echo PYTHONPATH: $$PYTHONPATH
	$(PYTHON) -m pytest

.PHONY: clean
clean: venv
	$(PYTHON) setup.py clean

.PHONY: distclean
distclean: clean
	$(RM) -R build dist *.egg-info venv rr-2.0 rr-2.0-java11.zip

venv:
	python3 -m venv venv
	$(PIP) install -r requirements.txt

rr-2.0-java11.zip:
	curl -LO https://github.com/GuntherRademacher/rr/releases/download/v2.0/rr-2.0-java11.zip

rr.war: rr-2.0-java11.zip
	unzip $< $@
	touch $@
