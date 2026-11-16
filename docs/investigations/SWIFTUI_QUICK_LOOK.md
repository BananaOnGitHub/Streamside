# Native stream Quick Look trial

Implementation starts from `97e1396` on `feat/native-frontend`, following device
acceptance of the tag display. That acceptance is a visual user observation,
not a new RN/Hermes counter report.

Holding a live thumbnail for half a second opens a bounded, scrollable native
preview over the feed. A separate UIKit hold/tap recognizer pair prevents release
after a successful hold from also watching; scroll drags can cancel both. Direct
thumbnail taps still watch, and VoiceOver has a named preview action.

The existing owned SSNPlayback facade and authenticated Twitch GraphQL/IVS path
supply video. Mute intent is set before start and applied before IVS load/play;
it survives background teardown/recreation. No new donor ABI or credential path
is introduced. The exact donor is revalidated during local packaging.

Preview details reuse the cached avatar, current feed metadata and existing live
beacon (including cycle and Reduce Motion preferences). The full title is not
line-limited. Tags wrap in native order using the same Liquid Glass pills; every
admitted tag is rendered, including an individually long tag wrapping onto
multiple lines. Source safety limits still apply: up to 32 names from the native
feed, at most 256 UTF-16 units each. The card scrolls if details exceed its height.
View profile is deliberately disabled pending its separate implementation.

Watch, including a tap on the video, reuses the same player facade and media view
inside the existing portrait theatre. An owned UIKit container crossfades the
preview out and theatre in on the same 350 ms timeline (200 ms under Reduce
Motion), instead of presenting another modal sheet. Preview remains muted until
the handoff finishes. Duplicate Watch actions are ignored. Closing during the
fade stops media and cannot subsequently unmute it. Normal close, account loss
and background behavior retain the existing cancellation/session checks. The
window root, native login ownership and RN/Hermes guards remain in place.

## Validation plan and initial host results

Linux native regression suite: **72 tests passed**, including rejection of a
missing Quick Look simulator receipt. This does not establish Apple compilation.
Hosted validation adds real UIKit containment/compositor checks for paired fade
opacities, single handoff, close during transition and teardown; wrapping of all
tags with an oversized Unicode tag; and actual coordinate hold/tap/scroll checks.
The synthetic IVS facade test also requires mute to be set at media load. These
fixtures contain no donor, credentials or real stream content. Hosted compilation,
verified download and local packaging outcomes will be appended with identities.

## Device check

Install the candidate using Feather. Hold a live thumbnail: confirm muted video,
full title, all tags, avatar beacon and disabled View profile. Release the hold;
it should remain a preview. Tap the video or Watch: check a direct fade into the
theatre, audio beginning after the transition and working player controls. Close
back to the unchanged feed. Try outside-tap dismissal, scrolling the feed and a
long preview, repeated opens, background/foreground and closing during the fade.
Check Reduce Motion/larger text and export native diagnostics after preview and
Watch. Real authenticated playback/audio, animation appearance and unchanged zero
RN/Hermes counts require physical-device evidence.

## Hosted and packaged result — 2026-11-16

Source `b89c3f3b7d1e76013b12e2a1b09a9d3cd47130bb` passed
[Codemagic build `6afaa4ba90e83b09c4fadda0`](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afaa4ba90e83b09c4fadda0)
in **703.429 seconds** (11m 43s). The quota selector verified 465 free minutes
before submission. Xcode 26.6 / 17F113 and iPhoneOS SDK 26.5 matched the pin.
Both owned frontend components compiled and linked, Swift models passed, and
all mandatory simulator receipts passed. The three coordinate tests include
actual thumbnail hold/release, tap and scroll cancellation, plus the existing
Liquid Glass/plain controls. Paired intermediate compositor opacities and final
containment verified the preview/theatre fade and cancellation behavior in an
owned synthetic fixture. Foundation networking, logging, report comparison and
build-routing gates passed. Linux and documentation workflows passed. There
were no failed or skipped required gates and no duplicate Apple/VM build.

Verified download admitted source/input hashes, toolchain, archive and required
receipts. **53 Ubuntu post-download tests passed** (18 ABI, 15 component admission,
10 diagnostic core, one launch policy, six probes and three launch comparisons).
Local packaging revalidated the exact donor SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`,
all 12 pinned images and existing ABI contracts, then verified every retained
donor entry and unchanged original HBC. No new donor-specific service call or
ABI entry was needed. Only the native IPA was assembled; donor and IPA stayed
local, and no signing material was transferred to CI.

Candidate `quick-look-b89c3f3/StreamsideNativeProof-Twitch32-native.ipa` is
**196,850,156 bytes**, SHA-256
`7cbe4d14d4e2be0e56960d805f21f982aa58448cd791d1ac352d5fa360d3cc7b`.
It lives under the sibling `artifacts/native-frontend/` directory and requires
local Feather signing with the existing app identity. The owned archive hash is
`0e8f965762ff7a3fd091bdaee77a059780297005d3b79476d3047f530e7b78b1`.
[Structured evidence](SWIFTUI_QUICK_LOOK_VALIDATION.json) records identities,
workflow links and gate receipts. Packaging/verification logs remain outside Git.

Build path: commit/push the source, run `make native-ci` once, then
`make native-ci-status` and `make native-ci-fetch`. Assemble locally with
`python3 tools/native_frontend/build.py --frontend swiftui --components
../artifacts/ci/<source-sha>/download/components --donor
../donors/tv.twitch-32.0.ipa --output ../artifacts/native-frontend/<new-name>`.
The existing [Apple build guide](../development/APPLE_BUILDS.md) owns provider,
quota and fallback details. This successful build/package does not establish
real IVS preview rendering/audio, device transition appearance, login regression
or zero RN/Hermes activity: the device checks above remain pending.
