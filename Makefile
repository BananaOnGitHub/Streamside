.PHONY: all build test test-rn-virtualization verify clean deb release ipa

all: build

build:
	./build.sh

test:
	python3 -m unittest discover -s tests -v

# Required donor/Hermes regression check for RN library changes or Twitch ports.
# Unlike the optional unittest, this target cannot silently skip missing inputs.
test-rn-virtualization:
	@test -n "$(TAS_RN_DONOR)" -a -n "$(ZIG)" -a -n "$(TAS_HERMESC)" -a -n "$(TAS_HERMES_SNAPSHOT_RUNNER)" -a -n "$(TAS_HERMES_SOURCE)" || (echo 'set TAS_RN_DONOR, ZIG, TAS_HERMESC, TAS_HERMES_SNAPSHOT_RUNNER and TAS_HERMES_SOURCE' >&2; exit 1)
	python3 tools/validate_rn_snapshot.py --donor "$(TAS_RN_DONOR)" --zig "$(ZIG)" --hermesc "$(TAS_HERMESC)" --runner "$(TAS_HERMES_SNAPSHOT_RUNNER)" --runtime-source "$(TAS_HERMES_SOURCE)"

verify: build
	python3 tools/artifact_guard.py check build/Streamside.dylib
	python3 tools/artifact_guard.py check build/Streamside.framework --framework

deb: verify
	python3 tools/build_deb.py

# Local unsigned preparation only; no tag, workflow dispatch, or publication.
ipa: verify test
	@test -n "$(INPUT_IPA)" || (echo 'set INPUT_IPA=/path/to/decrypted.ipa' >&2; exit 1)
	@test -n "$(OUTPUT_IPA)" || (echo 'set OUTPUT_IPA=/path/to/output.ipa' >&2; exit 1)
	python3 tools/patch_ipa.py "$(INPUT_IPA)" --framework build/Streamside.framework --output "$(OUTPUT_IPA)"
	python3 tools/verify_ipa.py "$(OUTPUT_IPA)" --framework build/Streamside.framework

clean:
	rm -rf build dist

release: verify test deb
	python3 tools/package_release.py
