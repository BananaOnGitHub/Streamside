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
