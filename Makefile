NAME := sqlrepo
TESTS := tests
UV := $(shell command -v uv 2> /dev/null)

.DEFAULT_GOAL := install

.PHONY: install
install:
	@if [ -z $(UV) ]; then echo "UV could not be found."; exit 2; fi
	$(UV) install -G:all --no-self


.PHONY: shell
shell:
	@if [ -z $(UV) ]; then echo "UV could not be found."; exit 2; fi
	$(ENV_VARS_PREFIX) $(UV) run ipython --no-confirm-exit --no-banner --quick \
	--InteractiveShellApp.extensions="autoreload" \
	--InteractiveShellApp.exec_lines="%autoreload 2"

.PHONY: clean
clean:
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf ./logs/*

.PHONY: lint
lint:
	@if [ -z $(UV) ]; then echo "UV could not be found."; exit 2; fi
	$(UV) run pyright $(NAME)
	$(UV) run pyright $(TESTS)
	$(UV) run black --config ./pyproject.toml --check $(NAME) --diff
	$(UV) run black --config ./pyproject.toml --check $(TESTS) --diff
	$(UV) run ruff check $(NAME)
	$(UV) run ruff check $(TESTS)
	$(UV) run vulture $(NAME) --min-confidence 100 --exclude "*/types.py,*/logger.py,*/abc.py"
	$(UV) run vulture $(TESTS) --min-confidence 100 --exclude "*/types.py,*/logger.py,*/abc.py"

.PHONY: fix
fix:
	@if [ -z $(UV) ]; then echo "UV could not be found."; exit 2; fi
	$(UV) run black --config ./pyproject.toml $(NAME)
	$(UV) run black --config ./pyproject.toml ./$(TESTS)
	$(UV) run ruff check $(NAME) --config ./pyproject.toml --fix
	$(UV) run ruff check $(TESTS) --config ./pyproject.toml --fix

.PHONY: tests
tests:
	@if [ -z $(UV) ]; then echo "UV could not be found."; exit 2; fi
	$(UV) run coverage run -m pytest -vv
	$(UV) run coverage xml
	$(UV) run coverage report --fail-under=95

.PHONY: quality
quality:
	make fix lint tests
