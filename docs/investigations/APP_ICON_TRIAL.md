# 3.1.0 build 1 — flat app-icon trial

Branch: `dev/3.1.0`. Target donor: Twitch 31.5 (`262752111271985979`).
This is a sideload packaging experiment. Build 1 installation, the Streamside icon,
and automatic Liquid Glass conversion were confirmed on-device. The iOS/device
and signing configuration were not recorded, so this is scoped trial evidence.

## Input and scope

The 1024×1024 logo is identical to [the repository logo](../assets/streamsidelogo.png),
SHA-256 `cc26979d86e7aca9147fa40db2c857408b65af8ffff4c12f7afbd09b5235f4b6`.
It has an alpha channel, but every pixel is opaque. The committed bundle PNGs are RGB,
with no alpha channel, custom appearance variants, masks, or baked-in glass effects.

The input IPA is the previously tested 3.0.0 candidate promoted to the published release:
SHA-256 `fb8dada2a79520f83b5f4302253b1e1a6d1c7afea581acf88ef68a12ffe6e436`.
The framework is rebuilt from this branch as public version `3.1.0`, internal bundle
`3.1.0.1`, and diagnostic label `3.1.0-build.1`. Twitch's application version/build stay unchanged.

## Packaging seam

[app_icons.py](../../tools/app_icons.py) supplies loose PNGs from
[packaging/app-icons](../../packaging/app-icons). The phone primary-icon list covers
29-, 40-, and 60-point bases at 2×/3×. The iPad list includes those bases plus 76-point
1×/2× and 83.5-point 2× icons, with iPad-specific settings/Spotlight files. A 1024-pixel
reference is also carried in the bundle.

[patch_ipa.py](../../tools/patch_ipa.py) changes the primary icon's `CFBundleIconFiles`
and removes its `CFBundleIconName`, which otherwise points to Twitch's asset catalog.
The same treatment applies to `CFBundleIcons~ipad`. Legacy top-level icon selectors
are removed. `UIPrerenderedIcon` is false for the new flat artwork.

Native alternate-icon declarations, unrelated primary-icon metadata, bundle identity,
Twitch version, SDK/minimum-iOS metadata, extension bundles, and the original icon
files remain intact. `Assets.car` is byte-preserved and hash-checked; it is not edited,
recompiled, or replaced. Repatching replaces owned Streamside PNGs without duplicate entries.

This does not change the icon of a stock Twitch installation through a jailbreak DEB.
The trial changes the sideload IPA's bundle resources and metadata only.

## Liquid Glass boundary

Apple's [app-icon guidance](https://developer.apple.com/design/human-interface-guidelines/app-icons)
states that the system generates appearance variants that an app does not provide.
This trial provides only the default flat icon, leaving dark, clear, and tinted
appearances to iOS. It does not provide layered Icon Composer artwork.

The donor sets `UIDesignRequiresCompatibility=YES` and `UIPrerenderedIcon=YES`.
The trial changes the icon's pre-rendered flag but preserves the app-wide compatibility
setting. It also leaves the donor's SDK metadata unchanged. Default icon effects under
that combination were subsequently confirmed in the build-1 device trial; this is
observed appearance evidence, not a package-check result.
Apple's [Liquid Glass overview](https://developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass)
and [Icon Composer guide](https://developer.apple.com/documentation/Xcode/creating-your-app-icon-using-icon-composer)
describe the separate layered-icon route.

## Checks and acceptance

[test_app_icons.py](../../tests/test_app_icons.py) covers metadata preservation,
sizes/opacity, malformed PNG refusal, exact packaged bytes, corruption refusal,
idempotent repatching, independent verification, and direct CLI use.
[verify_ipa.py](../../tools/verify_ipa.py) requires the committed icon bytes and primary
selectors in addition to the existing binary/resource contract. Developer bundles
carry the helper and all icon files so direct patching still works offline.

Build-1 host validation: 161 tests run, 158 passed, three skipped (Apple Foundation
and two private donor/Hermes checks). All nine icon tests passed. Native framework/dylib
verification, both DEB builds, and developer-bundle verification passed. These results
do not establish the Home Screen appearance or jailbreak-device behavior.

Remaining device evidence and follow-up checks:

- Sign and install the build as an update; confirm settings and recent emotes remain.
- Confirm the default Streamside logo in the Home Screen, App Library, search, and Settings.
- Compare dark, tinted light/dark, and clear light/dark appearances, including small/large icons.
- Record iOS/device, signing tool, screenshot, clipping/contrast, and any stale Twitch icon.
- If an old icon persists, distinguish signer icon overrides and SpringBoard caching from bundle metadata.
- Check launch and the existing chat/playback behavior. Do not infer those results from icon verification.

Public feature, installation, compatibility, and changelog documents remain at the
published 3.0.0 baseline until feature freeze, per [Documentation maintenance](../development/DOCUMENTATION.md).
