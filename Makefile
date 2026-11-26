STREAMSIDE_ARTIFACTS_DIR ?= $(abspath ../artifacts)
export STREAMSIDE_ARTIFACTS_DIR
PYTHONDONTWRITEBYTECODE ?= 1
export PYTHONDONTWRITEBYTECODE
NATIVE_CI_PYTHON ?= python3
NATIVE_CI_TEST_PATH ?= $(abspath ../toolchains/python)
export PYTHONPATH := $(NATIVE_CI_TEST_PATH):$(PYTHONPATH)

# Zig is used as a cross-compiler for the Ubuntu ABI/header fixtures.
HOST_TESTS := abi build_progress comparison components context_preview_evidence coordinate_gates core launch launch_comparison playback_header probes vaft_core
DONOR_TESTS := admission content_labels cursor_witness feed_contract profile_contract

.PHONY: all test test-host test-donor docs-check native-ci-plan native-ci native-ci-status native-ci-fetch

all: test

docs-check:
	$(NATIVE_CI_PYTHON) tools/check_docs.py

test: test-host test-donor

test-host:
	$(NATIVE_CI_PYTHON) -m unittest discover -s tests -v
	@set -e; for suite in $(HOST_TESTS); do $(NATIVE_CI_PYTHON) -m unittest discover -s tests/native_frontend -p "test_$$suite.py" -v; done

test-donor:
	@set -e; for suite in $(DONOR_TESTS); do $(NATIVE_CI_PYTHON) -m unittest discover -s tests/native_frontend -p "test_$$suite.py" -v; done

# Select exactly one hosted Apple provider using current quota and build history.
native-ci-plan:
	$(NATIVE_CI_PYTHON) tools/apple_builds.py plan
native-ci:
	$(NATIVE_CI_PYTHON) tools/apple_builds.py start
native-ci-status:
	$(NATIVE_CI_PYTHON) tools/apple_builds.py status
native-ci-fetch:
	$(NATIVE_CI_PYTHON) tools/apple_builds.py fetch
