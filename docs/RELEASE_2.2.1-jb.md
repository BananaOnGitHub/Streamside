# TwitchAdBlock-VAFT-iOS 2.2.1

**This is the jailbreak .deb release, with versions for rootful (iphoneos-arm) and rootless (iphoneos-arm64) jailbreaks. I currently do not have any devices that can be jailbroken past 15.5, so I cannot test this. If you install this and it doesn't work, please file an issue!!**

## Changes

- Rebuilds both packages from the checked-in source containing the R5 opt-in
  diagnostic privacy labels and route history, shared with the sideload IPA.
- Retains the main Profile → Settings button fix and VAFT implementation.
- Removes the older diagnostic log containing request paths at initialization.

These packages passed build and layout checks. They have **not** been tested
on a jailbroken device.

## Packages

The package display name is **Twitch VAFT**.

- `dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb` — rootful.
- `dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb` — rootless (`/var/jb`).

SHA-256:

```text
7d2143260c5097e7c1a63d35649c3e20df9cb90301a2cb11ee29df11f2745c1d  dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb
e73ad6823b7da91dbac7b79336ae7173fb8023c81cf4be1b4bbdcf7ce25e0216  dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb
```
