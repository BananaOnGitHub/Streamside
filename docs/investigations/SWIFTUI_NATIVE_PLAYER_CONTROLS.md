# Native portrait player controls

## Implementation trial

The theatre now starts with the 16:9 video at the top of its safe content area.
There is no separate header or diagnostic button. The down chevron closes the
player and tears down media; it does not minimize. UIKit's portrait safe area
keeps the video and its 44-point control targets below the notch/Dynamic Island.
Portrait-only ownership, existing authentication return, runtime guards and
mode-specific diagnostics exports remain unchanged. The global two-finger
hold diagnostic gesture remains available.

Controls reveal on a video tap and hide after four seconds without interaction.
Every enabled action resets the timeout; a second background tap hides them.
Popovers and VoiceOver keep controls available. Reduce Motion disables custom
numeric transitions and control fading. Controls add only a six-percent black
scrim. Liquid Glass buttons default on, with a persistent toggle shared between
the player's small gear popover and Settings → Player. When off, buttons are plain
white glyphs. Reduce Transparency uses an opaque control/pill background.

The bottom-left live pill uses the existing one-second native clock, with
numeric text transitions for elapsed time and changed viewer counts. Viewers and
title metadata update through the existing authenticated account/followed-channel
GraphQL path every 30 seconds while the theatre is active, with the existing
five-second guard and in-flight protection. This deliberately reuses the admitted
native client rather than adding another request ABI. It does not invalidate or
refetch thumbnails. Polling stops with the theatre, skips inactive/failed/ended
playback, and retains the last known data when a request fails. Viewer counts are
server snapshots, not per-second estimated increments. Missing data is shown as
unavailable; no sample or public endpoint substitutes for native results.

Pause/resume operates on the existing IVS instance; pausing is distinct from
background teardown and does not trigger the load-stall deadline or READY-state
autoplay. Authorization continues to be checked while paused. Mute invokes only
IVSPlayer `setMuted:`. It does not touch system volume or change AVAudioSession
configuration. Pause and mute intent survive inactive media teardown/recreation.
A new start/retry resets pause; mute stays attached to the same theatre facade.
Closing, account invalidation and backgrounding still release media correctly.
Diagnostic playback phase 8 means user-paused; runtime counters are unchanged.

The share button opens a compact native popover with system glyphs: Copy link
(`doc.on.doc`), Share link (`square.and.arrow.up`) and disabled Whisper (`message`).
Copy writes only the validated public HTTPS channel URL after a user tap. Share
uses the system ShareLink sheet; no media grants or account credentials reach it.
Whispers are deferred. The clapper-only clip button (`movieclapper`) and fullscreen
glyph (`arrow.up.left.and.arrow.down.right`) are disabled placeholders for the
requested later clip/landscape work. Casting is also disabled as described below.

Settings keeps Account first, separate drill-in pages for Followed streams
(filled heart) and Player, then Diagnostics. Existing feed preferences, Liquid
Glass cycle slider, haptics and Reduce Motion behavior are preserved.

## Native service admission and casting blocker

[Bounded exact-donor inspection](evidence/native-player-controls/native-service-inspection.json)
identifies the inspected Twitch 32.0 donor and image hashes. Native Chromecast
UI exists: `_TtC6Twitch16ChromecastButton` and
`_TtC6Twitch17ChromecastManager` implement a native UIKit action path. The cast
button reads Twitch's app delegate and assigns its native manager as delegate;
the action uses native actions and GoogleCast session/media services. This is
separate from `TwitchRNHostCast`, whose exposed picker/cast methods are RN host
APIs and are not used. Finding native UI alone does not establish a safe stream
handoff: the currently active media is our owned IVS facade, not a Twitch player
coordinator session. No validated manager-access/context and media ownership
contract has been established for that handoff. Creating a manager from an
exposed init or guessing Swift storage/witness dispatch would not satisfy ABI
admission. No casting adapter, discovery/session mutation or picker was installed.

The donor also has `TwitchRNAirPlayPlayerView` and its RN manager. Those are not
used. [Amazon's IVS documentation](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/player.html)
requires a separate AVPlayer transition for AirPlay; adding an AirPlay picker
alone would not make this IVS video cast. AirPlay/Chromecast remain blocked pending
a validated native session handoff. No alternative casting implementation was
attempted after that boundary.

The mute setter is statically admitted by exact class/selector, Objective-C type
encoding `v20@0:8B16`, address `0x61a00` and instruction prefix in the identity-pinned
AmazonIVSPlayer image. It is also checked at runtime before player creation.
The donor plan now admits 51 Swift ABI entries, 12 Objective-C services and
25 runtime probes. Existing play/pause calls use previously admitted boundaries.
[IVS's mute reference](https://aws.github.io/amazon-ivs-player-docs/1.16.0/ios/Classes/IVSPlayer.html)
describes player-local audio muting; donor inspection, not an assumed SDK version,
defines the actual boundary. [Apple Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
and [Liquid Glass](https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:))
references inform the accessibility/effect gating.

## Validation and device checklist

Host tests validate exact donor admission, rejection of altered mute encoding or
prefix, existing runtime guard behavior and build admission. Apple CI compiles the
real SwiftUI overlay and interoperability layer. Pure model fixtures cover control
timeout/interaction/VoiceOver hold behavior and public URL validation. Synthetic
UIKit/IVS fixtures additionally require local pause/resume, unchanged system
volume/audio category on mute, mute/pause intent retention through background
recreation, and account invalidation while paused, alongside existing decoded
frame, cancellation and release checks. These fixtures have no donor, actual
video/audio or physical route devices. Actual button layout, glass/readability,
share presentation, audio muting and zero RN/Hermes on these new interactions
remain physical-device checks.

1. Install the new Native IPA with Feather using the same app identity. Open a
   live followed channel. Check the top video/chevron are clear of the notch.
2. Wait four seconds: controls disappear. Tap to reveal, pause/resume, mute/unmute.
   The stream should pause/mute; the device volume must stay unchanged.
3. Check the live clock ticks; leave it open for 30–60 seconds for real viewer
   metadata refresh. Changed viewer counts animate; unchanged values stay still.
4. Open Share: Copy link should copy the public channel URL; Share link should
   open the system sheet. Whisper, clips, fullscreen and cast are disabled.
5. Toggle Liquid Glass in the player gear popover and in Settings → Player; the
   preference must agree and persist. Check the separate Followed streams page.
6. Enable Reduce Motion: numbers and control visibility update without custom
   animation. Check Reduce Transparency and VoiceOver if available.
7. Pause and mute, background/return, resume/unmute, close with the chevron, reopen
   another stream. Check audio stops on close and login/session behavior survives.
8. Export Native diagnostics from Settings (or the two-finger hold). After an
   original-mode positive control for this source, guarded RN/Hermes/worklet counts
   must stay zero through all controls and lifecycle actions, all images armed,
   no failures. Original routing is still a one-shot cold launch; exports stay
   mode-specific. No new independent baseline IPA is needed for this UI trial.

Source revision, CI outcomes and the single Native package identities are added
below after compilation and local donor-dependent packaging.
