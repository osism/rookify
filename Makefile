COLOUR_GREEN=\033[0;32m
COLOUR_RED=\033[0;31m
COLOUR_BLUE=\033[0;34m
COLOUR_END=\033[0m

.DEFAULT_GOAL:=help
SHELL:=/bin/bash


## checking if docker, or podman should be used. Podman is preferred.
ifeq ($(shell command -v podman 2> /dev/null),)
	CONTAINERCMD=docker
else
	CONTAINERCMD=podman
endif

# Checking if python exists
ifneq (, $(shell command -v python))
    $(info Python is installed as 'python')
    PYTHON := $(shell command -v python)
else ifneq (, $(shell command -v python3))
    $(info Python3 is installed as 'python3')
    PYTHON := $(shell command -v python3)
else
    $(error Neither python nor python3 is installed)
endif

## Export default rookify version
export ROOKIFY_VERSION?=0.0.0.dev1

.PHONY: help
help: ## Display this help message
	@echo -e '\n${COLOUR_BLUE}ROOKIFY MAKEFILE${COLOUR_BLUE}'
	@echo -e '\n${COLOUR_RED}Usage: make <command>${COLOUR_END}'
	@cat $(MAKEFILE_LIST) | grep '^[a-zA-Z]'  | \
	    awk -F ':.*?## ' 'NF==2 {printf "  %-26s%s\n\n", $$1, "${COLOUR_GREEN}"$$2"${COLOUR_END}"}'
	@echo -e '${COLOUR_RED}OSISM helperscript usage: make <command>${COLOUR_END}'
	@cat $(MAKEFILE_LIST) | grep '^[a-zA-Z]'  | \
	    awk -F ':.*?#osism# ' 'NF==2 {printf "  %-26s%s\n\n", $$1, "${COLOUR_GREEN}"$$2"${COLOUR_END}"}'

.PHONY: setup
setup: check-radoslib setup-venv setup-pre-commit ## Setup the pre-commit environment and then the venv environment

.PHONY: setup-pre-commit
setup-pre-commit:
	./.venv/bin/pip install --user pre-commit && ./.venv/bin/python -m pre_commit install

.PHONY: setup-venv
setup-venv:
	${PYTHON} -m venv --system-site-packages ./.venv && \
	./.venv/bin/pip install -r requirements.txt

.PHONY: run-precommit
run-precommit: ## Run pre-commit to check if all files running through
	pre-commit run --all-files

.PHONY: update-requirements
update-requirements: ## Update the requirements.txt with newer versions of pip packages
	source ./.venv/bin/activate && \
	pip freeze -l > requirements.txt

.PHONY: check-radoslib
export RADOSLIB_VERSION:=2.0.0
check-radoslib: ## Checks if radoslib is installed and if it contains the right version
	# Get needed paths and information from locally installed librados
	./scripts/check_local_rados_lib_installation.sh ${RADOSLIB_VERSION}

.PHONY: build-local-rookify
build-local-rookify: ## This builds rookify into .venv/bin/rookify
	source .venv/bin/activate && pip install -e .

.PHONY: build-container
build-container: ## Build container from Dockerfile, add e.g. ROOKIFY_VERSION=0.0.1 to specify the version. Default value is 0.0.0.dev1
	${CONTAINERCMD} build --build-arg ROOKIFY_VERSION=$(ROOKIFY_VERSION) --target rookify -t rookify:latest -f Dockerfile .

.PHONY: run-local-rookify
run-local-rookify: ## Runs rookify in the local development environment (requires setup-venv)
	if [ ! -f ./.venv/bin/rookify ]; then \
		${MAKE} build-local-rookify; \
	fi; \
	.venv/bin/rookify

.PHONY: run-rookify
run-rookify: ## Runs rookify in the container
	docker exec -it rookify-dev /app/rookify/.venv/bin/rookify

.PHONY: get-testbed-configs-for-rookify-testing
get-testbed-configs-for-rookify-testing: ## Gets the needed config (like .kube, /etc/ceph and so on) from the testbed
	bash ./scripts/get_configs_from_testbed.sh

.PHONY: run-tests-locally
run-tests-locally: ## Runs the tests in the tests directory. NB: check that your local setup is connected through vpn to the testbed!
	.venv/bin/python -m pytest

.PHONY: run-tests
run-tests: up ## Runs the tests in the container
	${CONTAINERCMD} exec -it rookify-dev bash -c "/app/rookify/.venv/bin/python -m pytest"

.PHONY: enter
enter: ## Enter the container
	${CONTAINERCMD} exec -it rookify-dev bash

.PHONY: logs
logs: ## Logs the container
	${CONTAINERCMD} logs -f rookify-dev

.PHONY: down
down: ## Remove the containers as setup by docker-compose.yml
	${CONTAINERCMD} compose down

.PHONY: up
up: ## Sets up the container as specified in docker-compose.yml and opens a bash terminal
	${CONTAINERCMD} compose up -d

##
# Add osism specific scripts below here (so they appear below helper header)
##

.PHONY: get-config
get-config: #osism# Gets configuration files from the OSISM testbed
	./scripts/osism/get_osism_configs_from_testbed.sh
