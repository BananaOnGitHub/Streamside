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

- `dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb` — rootful.
- `dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb` — rootless (`/var/jb`).

SHA-256:

```text
23349a3ab7c0edd72dbfe7f8fb5c9e6a2dea8b491f8340db9df4a00ce1e33d32  dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb
43a9a52198c378b990ce2a9eb1975763696de1d631353e7935fca877aa902255  dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb
```
