# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make" mode.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Custom targets for DocuMind
clean:
	rm -rf $(BUILDDIR)/*

livehtml:
	sphinx-autobuild -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."
	@echo "Live reload server running at http://127.0.0.1:8000"

coverage:
	$(SPHINXBUILD) -b coverage . $(BUILDDIR)/coverage
	@echo
	@echo "Build finished. Check the coverage in $(BUILDDIR)/coverage."

linkcheck:
	$(SPHINXBUILD) -b linkcheck . $(BUILDDIR)/linkcheck
	@echo
	@echo "Link check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/linkcheck/output.txt."

spelling:
	$(SPHINXBUILD) -b spelling . $(BUILDDIR)/spelling
	@echo
	@echo "Spell check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/spelling/."

# Development targets
dev-install:
	pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints sphinxcontrib-django sphinx-autobuild

dev-serve:
	sphinx-autobuild . _build/html --host 0.0.0.0 --port 8080

# Production targets
build-prod:
	$(SPHINXBUILD) -b html . $(BUILDDIR)/html -E -W

# Auto-generate API docs
apidoc:
	sphinx-apidoc -o modules ../documind --force --separate
	@echo
	@echo "API documentation generated. Run 'make html' to build."