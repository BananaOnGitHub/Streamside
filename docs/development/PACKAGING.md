# Packaging and binary contracts

Packaging must carry the bytes actually verified from a build. Source labels, filenames, and version strings cannot substitute for binary identity.

## Two identities

| Route | Binary/install identity |
| --- | --- |
| Sideload IPA | `Streamside.framework/Streamside`, required `@rpath/Streamside.framework/Streamside` |
| Jailbreak | `Streamside.dylib`, `@rpath/Streamside.dylib` |
| Debian package | `dev.tas.twitchadblock`, retained for upgrade continuity |

Both native artifacts come from the same source. Initialization uses the native constructor, not a historical donor runtime.

## Build normalization and fingerprints

`build.sh` cross-compiles each identity, normalizes segment geometry, finalizes its signature representation, and only then records its adjacent `.macho.json` receipt.

[align_macho_segments.py](../../tools/align_macho_segments.py), [reserve_codesign_space.py](../../tools/reserve_codesign_space.py), and [shrink_adhoc_signature.py](../../tools/shrink_adhoc_signature.py) belong to build preparation. Package admission does not silently run them over a mismatched input.

Checks cover 16 KiB segment ranges, offsets/sizes/gaps/overlaps, section containment, linkedit bounds, exact install/signing identity, signature placement/reservation, CodeDirectory executable range, and every code-page hash.

The dylib keeps a 64 KiB replacement-signature reservation. The framework uses the compact signed form expected by the tested sideload path. Neither output should be substituted for the other merely because both contain the same native sources.

## IPA patching

[patch_ipa.py](../../tools/patch_ipa.py) refuses encrypted/unsupported executables and incomplete inputs. It requires the framework fingerprint and compares current bytes/metadata before patching.

It removes historical injected dylib/framework load commands and components, then adds exactly one required Streamside framework load using existing Mach-O header padding. A weak load is not an acceptable substitute.

Unrelated entries remain intact. The complete `Assets.car` is required and its finished bytes are verified. Historical missing/truncated assets caused signed-in scene-creation crashes despite reaching login.

Output is written to a temporary archive. [verify_ipa.py](../../tools/verify_ipa.py) reads the finished package and checks framework bytes against the verified build, app load/signature geometry, and preserved resources before the output filename is atomically installed.

The prepared IPA is unsigned for the installation tool. Verification of pre-signing bytes does not imply a third-party signer's result remains byte-identical.

## DEB preparation

[build_deb.py](../../tools/build_deb.py) builds rootful `iphoneos-arm` and rootless `iphoneos-arm64` packages. Rootless paths use `/var/jb`; injection filters scope the tweak to `tv.twitch`.

The package declares the existing TwitchAdBlock conflict because both tweaks intercept the same playback stack. Data archives are read back and their dylib bytes compared with the verified build.

A successful DEB build is not on-jailbreak device validation.

## Developer bundles

[package_release.py](../../tools/package_release.py) creates local framework/dylib/DEB bundles and checksums. `checked_zip()` validates archive integrity, duplicate entries, exact source bytes, and packaged binaries before replacement. Receipts are rechecked after packaging to detect a staging race.

The documentation layout requires the bundle to include root entry points, the `docs/` tree, and license notices at their new paths. Relative documentation links must remain usable offline within the bundle. This is a packaging dependency of the documentation move, not a runtime feature.

Public standard releases remain IPA-only. Separate `-jb` prereleases are DEB-only. Local developer ZIPs/checksums are not automatically public release attachments.

`make release` prepares these local artifacts; it does not create a GitHub tag or release. Bundle provenance includes the source commit, public `VERSION`, internal bundle version, and target Twitch donor. Keep fingerprints tied to the exact packaged bytes; changed bytes or metadata require verification again. Device evidence is covered in [Testing](TESTING.md), and established installation configurations in [Compatibility](../COMPATIBILITY.md).

## Failure handling

Missing receipt, changed framework metadata, corrupt code pages, mismatched archived binary, malformed load commands, or incomplete app resources stop packaging. Do not regenerate a receipt over arbitrary bytes just to pass.

Rebuild from the intended source with `make verify`, retain the complete outputs/receipts, and package those exact artifacts. Matching source labels do not establish packaged equivalence.

## Historical correction

The final 2.3.0 framework lost segment normalization even though its main app executable matched working dev.8. Rename/path trials inherited that same bad framework and initially implicated the loader identity incorrectly.

Restoring rounded segment ranges and compact signing metadata reproduced the working source-built framework. The subsequent Streamside-identity migration launched. [History](../HISTORY.md#the-unpublished-231-transition) retains the correction and prevents the obsolete filename explanation from becoming a current architectural claim.

[Artifact guard tests](../../tests/test_artifact_guard.py) recreate the unrounded regression and corrupt finished archives. [Tool tests](../../tests/test_tools.py) cover injection/assets/unsupported input. [Testing](TESTING.md) owns execution evidence.
