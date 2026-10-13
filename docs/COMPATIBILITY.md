# Compatibility

Compatibility is a combination of app binary, runtime ABI, installation method, and observed behavior. A successful build or a matching version label is not enough by itself.

## Current target

| Item | Released 3.0.0 target |
| --- | --- |
| Twitch app | 31.5 |
| Twitch build | 262752111271985979 |
| Architecture | arm64 |
| Inspected donor iOS minimum | 16.4 |
| Streamside public version | 3.0.0 |
| Framework internal bundle | 3.0.0.92 |
| Framework metadata minimum | 15.0; not the effective Twitch 31.5 minimum |
| RN source | Hermes 98, 27,786,480-byte original body |

Original Hermes SHA-256:

```text
422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b
```

The exact RN source fingerprint and function metadata gate component changes. Merely renaming a different app as “31.5” cannot satisfy them.

Twitch 31.6 (`262821841498166537`) is not admitted by the current RN patch
chain. Its Hermes-98 body has changed in size, checksum, and function count;
the production gate rejects it without modifying the input. The
[31.6 investigation](investigations/TWITCH_31_6_COMPATIBILITY.md) records the
native inspection and remaining port/testing requirements. Static native
similarities do not establish support for that donor.

## Both theatre/chat paths

The inspected donor includes RN/Hermes/Fabric and legacy UIKit/Swift chat. Device observations associated horizontal-only broadcasts with RN and horizontal/vertical broadcasts with legacy. Streamside retains both implementations.

That distribution is not a future-version selector rule. Device rotation is not the admission mechanism. A donor update needs renewed observation of actual ingress, composer, and rendering boundaries.

## Recorded feature evidence

| Area | Recorded result and limit |
| --- | --- |
| RN incoming static/animated emotes | Build-55 reports established observed rendering/continued animation; proportional tested cases confirmed in build 56 |
| RN ordinary sent messages | Build 60 corrected disappearance; device checks established tested sent-message/emote rendering |
| RN composer | Builds 62–64 established images, proportions, and first-download GIF startup |
| RN details, unified suggestions, library | Completed device-confirmed integrations in builds 66–70 |
| RN virtualization | Build 78 stationary/open/reopen behavior corrected; counts are JS instances, not physical native views |
| Cache reuse | Build-82 E→F delta established warm direct-cache reuse in that run |
| Legacy picker | Build 86 fixed initial native Recent; build 87 fixed footer tint/reparented insertion |
| Library names and keyboard predictions | Build 88 labels and build 89 provisional-input guard confirmed in subsequent checks |
| RN Reload Emotes | Build 91 placement and build 92 pressed highlight confirmed |
| RN action messages | Separate `/me` handler is unchanged; ordinary sent-message evidence does not establish support |
| Overlay/zero-width emotes | Not implemented by the proportional-width alias scheme |

Detailed evidence and corrections live in [History](HISTORY.md) and the [archive](archive/README.md). A confirmed example is not a claim that every emote format or every stream was tested.

## Installation evidence

The public 2.2.0/2.3.0 descriptions name Twitch 30.4.2, iPhone 16 Pro, iOS 18.2, and earlier ESign/LiveContainer/ZSign testing. Preserve those as historical configurations rather than extending them to every 3.0.0 device/signer combination.

The 3.0.0 IPA promotes the tested RC.1 artifact unchanged after on-device acceptance. The exact iOS/device/signer configuration was not recorded with that acceptance, so it does not establish a complete 3.0.0 compatibility matrix or extend the historical signer results above.

The source builds a verified framework for unsigned IPA patching and standalone rootful/rootless DEBs. Those are supported packaging routes.

Jailbreak releases are separate `-jb` prereleases. Their package build/layout tests do not establish on-jailbreak runtime success. Earlier jailbreak release warnings remain applicable.

## Playback acceptance

VAFT uses Foundation/AVFoundation boundaries, so its compatibility is not identical to the RN emote donor gate. Twitch can change token operations, manifests, markers, or player routing independently.

Clean playback and zero ad-marked counters in a 31.5 session do not prove preroll/midroll suppression. An ad-blocking acceptance claim requires an actual ad-bearing case, the attempted strategy, and the visible result. General on-device acceptance and existing emote confirmation do not establish that specific playback evidence.

## Unsupported donors and fallback

Native adapters validate required classes, encodings, field spans, alignment, and live ownership. RN patches validate original body/checksum/function metadata. Unsupported paths leave native behavior or literal text where possible.

A partial set of installed hooks is visible in diagnostics. Do not force an incompatible donor through a removed marketing-version guard, guessed offset, or regenerated fingerprint.

Package admission is stricter: invalid binary layout/signature/receipt or changed packaged bytes causes a hard failure. See [Packaging](development/PACKAGING.md).

[README installation](../README.md#installation) · [Twitch internals](development/TWITCH_INTERNALS.md) · [Testing](development/TESTING.md)
