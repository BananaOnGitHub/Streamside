.PHONY: all build test verify clean deb release ipa

all: build

build:
	./build.sh

test:
	python3 -m unittest discover -s tests -v

verify: build
	python3 tools/artifact_guard.py check build/TwitchAdBlock.dylib
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
