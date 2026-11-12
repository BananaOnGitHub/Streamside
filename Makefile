STREAMSIDE_ARTIFACTS_DIR ?= $(abspath ../artifacts)
export STREAMSIDE_ARTIFACTS_DIR
NATIVE_BUILD_DIR := $(STREAMSIDE_ARTIFACTS_DIR)/build
NATIVE_DIST_DIR := $(STREAMSIDE_ARTIFACTS_DIR)/dist

.PHONY: all build test test-rn-virtualization test-foundation-cache verify clean deb release ipa docs-check

all: build

build:
	./build.sh

docs-check:
	python3 tools/check_docs.py

test:
	python3 -m unittest discover -s tests -v

# Mandatory Apple HTTP integration: unlike ordinary Linux tests, cannot skip.
test-foundation-cache:
	@python3 -c 'import platform,shutil; assert platform.system()=="Darwin" and shutil.which("xcrun"), "Apple Foundation/Xcode required; this gate cannot skip"'
	python3 -m unittest discover -s tests -p test_foundation_cache.py -v

# Required donor/Hermes regression check for RN library changes or Twitch ports.
# Unlike the optional unittest, this target cannot silently skip missing inputs.
test-rn-virtualization:
	@test -n "$(TAS_RN_DONOR)" -a -n "$(ZIG)" -a -n "$(TAS_HERMESC)" -a -n "$(TAS_HERMES_SNAPSHOT_RUNNER)" -a -n "$(TAS_HERMES_SOURCE)" || (echo 'set TAS_RN_DONOR, ZIG, TAS_HERMESC, TAS_HERMES_SNAPSHOT_RUNNER and TAS_HERMES_SOURCE' >&2; exit 1)
	python3 tools/validate_rn_snapshot.py --donor "$(TAS_RN_DONOR)" --zig "$(ZIG)" --hermesc "$(TAS_HERMESC)" --runner "$(TAS_HERMES_SNAPSHOT_RUNNER)" --runtime-source "$(TAS_HERMES_SOURCE)"

verify: build
	python3 tools/artifact_guard.py check "$(NATIVE_BUILD_DIR)/Streamside.dylib"
	python3 tools/artifact_guard.py check "$(NATIVE_BUILD_DIR)/Streamside.framework" --framework

deb: verify
	python3 tools/build_deb.py

# Local unsigned preparation only; no tag, workflow dispatch, or publication.
ipa: verify test
	@test -n "$(INPUT_IPA)" || (echo 'set INPUT_IPA=/path/to/decrypted.ipa' >&2; exit 1)
	@test -n "$(OUTPUT_IPA)" || (echo 'set OUTPUT_IPA=/path/to/output.ipa' >&2; exit 1)
	python3 tools/patch_ipa.py "$(INPUT_IPA)" --framework "$(NATIVE_BUILD_DIR)/Streamside.framework" --output "$(OUTPUT_IPA)"
	python3 tools/verify_ipa.py "$(OUTPUT_IPA)" --framework "$(NATIVE_BUILD_DIR)/Streamside.framework"

clean:
	python3 -c 'import shutil; from tools.workspace_paths import BUILD_DIR, DIST_DIR; [shutil.rmtree(p) for p in (BUILD_DIR, DIST_DIR) if p.exists()]'

release: verify test deb
	python3 tools/package_release.py

# Mandatory startup graft validation; builds fail if its receipt is stale.
test-investigation-runtime:
	@test -n "$(TAS_RN_DONOR)" -a -n "$(ZIG)" -a -n "$(TAS_HERMESC)" -a -n "$(TAS_HERMES_SNAPSHOT_RUNNER)" -a -n "$(TAS_HERMES_SOURCE)" || (echo 'set the pinned donor/Hermes toolchain inputs' >&2; exit 1)
	python3 tools/validate_investigation_runtime.py --donor "$(TAS_RN_DONOR)" --zig "$(ZIG)" --hermesc "$(TAS_HERMESC)" --runner "$(TAS_HERMES_SNAPSHOT_RUNNER)" --runtime-source "$(TAS_HERMES_SOURCE)"
