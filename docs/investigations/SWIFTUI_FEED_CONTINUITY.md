# Native feed continuity and title controls

Starts from clean `feat/native-frontend` at `02573d2`, with compiled feed source
`d534f4e7d9e2a72696513c05961b6f383bdbcb35`. Earlier source, findings and package
identities remain in [the followed-stream trial](SWIFTUI_FOLLOWED_STREAMS.md).

## Device review of the first feed build

[Supplied reports and assertions](evidence/swiftui-device-4/validation.json) preserve
all four JSON reports byte for byte and the original ZIP hash. The ZIP remains in
external artifacts. Matching d534 baseline launch 10 provides positive RN/Hermes/
worklet observations. Native launch 16 is calibrated, arms all four images (15),
has zero failures and all 25 entry counts zero. Root ownership and navigation guard
are 1. Account/list state 4 returns 100 records after four foreground activations
and two background transitions, at uptime 287853 ms. Footprint is 95734128 bytes;
this single snapshot is not a controlled performance benchmark.

The user reports that timers neither count nor animate, and content disappears
on backgrounding. Those are failures of the first feed UI, despite its successful
native request and runtime isolation. The supplied native-previous belongs to
older source 1c059c1 / proof f072ea03 and is excluded from matching-build restart
evidence. No checker or acceptance criterion is weakened.

## Changes

Routine foreground/manual account verification retains the existing in-memory
account and feed while the request is pending. Request generation cancellation
still rejects stale completions. A successful currentUser result with another
username removes the old feed before starting its request. Authoritative native
account notifications and sign-out still clear immediately; absent authorization,
failed currentUser verification, monitor and ABI failures cannot display stale
account data. A feed-only failure keeps the preceding verified account/list and
shows an explicit stale-list retry message. No credential or account persistence
is added to disk. A full process restart still restores through Twitch's services.
The existing owned window/root, scroll view and offline disclosure are retained
during ordinary refresh, rather than removed with a temporary checking screen.

A shared native one-second clock replaces the scenePhase-gated animation timeline
inside the UIKit hosting controller. UIKit active/resign notifications start/stop
its common-run-loop timer. It derives each value from Date and the native start
date, immediately catches up on resume, and updates only observing duration pills.
Reduce Motion continues to disable numeric transitions, not time updates; Reduce
Transparency and the small bottom-right capsule are preserved. The earlier timer
schedule claim is superseded by this correction. Apple's
[UIKit lifecycle notification](https://developer.apple.com/documentation/uikit/uiapplication/didbecomeactivenotification)
and [Reduce Motion environment value](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
are the public boundaries used here.

On iPhone, Settings contains a saved Two-line stream titles switch (default off).
Large accessibility text retains three lines. Holding a title for one second opens
a scrollable, selectable full-title sheet with a Done button; the row exposes an
equivalent VoiceOver action. Restricted thumbnails hide any previous image
immediately even when the row survives a refresh.

## Validation

Local native regression checks initially pass 46/46. Apple compilation, pure Swift
presentation tests, production clock lifecycle simulator test, package identities
and physical-device fixes are pending at this implementation checkpoint. The new
clock simulator fixture uses no Twitch donor/account; it tests real timer ticks,
stopping after resign-active and catch-up after becoming active. Components are
rejected when that receipt is absent or failed. No successful timer animation,
background continuity, account-switch safety or title-sheet device result is
claimed before the replacement build is installed.
