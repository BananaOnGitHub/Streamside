# TwitchAdBlock-VAFT-iOS 2.2.2

**This is the jailbreak .deb release, with versions for rootful (iphoneos-arm) and rootless (iphoneos-arm64) jailbreaks. I currently do not have any devices that can be jailbroken past 15.5, so I cannot test this. If you install this and it doesn't work, please file an issue!!**

## Changes

- Restores R5's opt-in, temporary diagnostic labels and playback route history
  in checked-in source shared with the new sideload IPA.
- Keeps the main Settings button fix and 2.2.0 VAFT implementation.
- Removes the older diagnostic log containing request paths at initialization.

These packages passed local build and layout checks. They have **not** been
tested on a jailbroken device.

## Packages

- `dev.tas.twitchadblock_2.2.2_iphoneos-arm.deb` — rootful.
- `dev.tas.twitchadblock_2.2.2_iphoneos-arm64.deb` — rootless (`/var/jb`).

SHA-256:

```text
11ff10976dd86f7cc193b1fc6b750748aa1bed8f770f27d83c3de18365e4e942  dev.tas.twitchadblock_2.2.2_iphoneos-arm.deb
af500f95ac6f9f8a17c2072a2af45fb583c5d9dbc7944aac48e5aec0682af76b  dev.tas.twitchadblock_2.2.2_iphoneos-arm64.deb
```
