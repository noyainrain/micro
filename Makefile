PYTHON=python3
PIP=pip3
NPM=npm

PIPFLAGS=$$([ -z "$$VIRTUAL_ENV" ] && echo --user) -U
NPMFLAGS=--no-save --no-optional

.PHONY: test
test:
	$(PYTHON) -m unittest

.PHONY: test-client
test-client:
	$(NPM) $(NPMFLAGS) -C client test

.PHONY: test-ext
test-ext:
	$(PYTHON) -m unittest discover -p "ext_test*.py"

.PHONY: test-ui
test-ui:
	$(NPM) $(NPMFLAGS) -C hello run test-ui

.PHONY: watch-test
watch-test:
	trap "exit 0" INT; $(PYTHON) -m tornado.autoreload -m unittest

.PHONY: watch-test-client
watch-test-client:
	$(NPM) $(NPMFLAGS) -C client run watch-test

.PHONY: type
type:
	mypy --show-error-codes -p micro

.PHONY: lint
lint:
	pylint -j 0 micro hello/hello.py
	$(NPM) $(NPMFLAGS) -C client run lint
	$(NPM) $(NPMFLAGS) -C hello run lint

.PHONY: check
check: type test test-client test-ext test-ui lint

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) -r requirements.txt
	@# Work around npm 7 uninstalling local dependencies if outside package with a symlink (see
	@# https://github.com/npm/cli/issues/2339)
	@# npm 6 unhoists production dependencies already present for client
	$(NPM) $(NPMFLAGS) -C hello install --only=prod
	@# Work around npm 7 update modifying package.json (see https://github.com/npm/cli/issues/3044)
	$(NPM) $(NPMFLAGS) -C client install --only=prod
	@# Remove conflicting selenium-webdriver copy for Hello
	$(NPM) $(NPMFLAGS) -C client uninstall --only=prod selenium-webdriver

.PHONY: deps-dev
deps-dev:
	$(PIP) install $(PIPFLAGS) -r requirements-dev.txt
	@# Work around npm 7 update modifying package.json (see https://github.com/npm/cli/issues/3044)
	$(NPM) $(NPMFLAGS) -C client install
	@# Remove conflicting selenium-webdriver copy for Hello
	$(NPM) $(NPMFLAGS) -C client uninstall selenium-webdriver
	@# npm 6 unhoists production dependencies already present for client
	$(NPM) $(NPMFLAGS) -C hello install --only=dev

.PHONY: show-deprecated
show-deprecated:
	git grep -in -C1 deprecate $$(git describe --tags $$(git rev-list -1 --first-parent \
	                                                     --until="6 months ago" master))

.PHONY: release
release:
	scripts/release.sh
	$(PYTHON) -m setup bdist_wheel
	twine upload dist/noyainrain.micro-$(VERSION)-py3-none-any.whl
	cd client && npm publish

.PHONY: clean
clean:
	rm -rf $$(find . -name __pycache__) .mypy_cache build dist
	$(NPM) $(NPMFLAGS) -C client run clean
	$(NPM) $(NPMFLAGS) -C hello run clean

.PHONY: help
help:
	@echo "test:            Run all unit tests"
	@echo "test-client:     Run all client unit tests"
	@echo "                 SAUCE_USERNAME:   Sauce Labs user for remote tests"
	@echo "                 SAUCE_ACCESS_KEY: Sauce Labs secret for remote tests"
	@echo "test-ext:        Run all extended/integration tests"
	@echo "test-ui:         Run all UI tests"
	@echo "                 BROWSER:       Browser to run the tests with. Defaults to"
	@echo '                                "firefox".'
	@echo "                 WEBDRIVER_URL: URL of the WebDriver server to use. If not set"
	@echo "                                (default), tests are run locally."
	@echo "                 TUNNEL_ID:     ID of the tunnel to use for remote tests"
	@echo "                 PLATFORM:      OS to run the remote tests on"
	@echo "                 SUBJECT:       Text included in subject of remote tests"
	@echo "watch-test:      Watch source files and run all unit tests on change"
	@echo "watch-test-client: Watch client source files and run all unit tests on change"
	@echo "type:            Type check the code"
	@echo "lint:            Lint and check the style of the code"
	@echo "check:           Run all code quality checks (type, test and lint)"
	@echo "deps:            Update the dependencies"
	@echo "deps-dev:        Update the development dependencies"
	@echo "show-deprecated: Show deprecated code ready for removal (deprecated for at"
	@echo "                 least six months)"
	@echo "release:         Make a new release"
	@echo "                 FEATURE: Corresponding feature branch"
	@echo "                 VERSION: Version number"
	@echo "clean:           Remove temporary files"
