# TwitchAdBlock-VAFT-iOS 2.2.1

**This is the jailbreak .deb release, with versions for rootful (iphoneos-arm) and rootless (iphoneos-arm64) jailbreaks. I currently do not have any devices that can be jailbroken past 15.5, so I cannot test this. If you install this and it doesn't work, please file an issue!!**

## Changes

- Restricts the Ad Block button to the main Profile → Settings screen, fixing
  its appearance on Chat Identity and other settings pages.
- Keeps the 2.2.0 source-built VAFT implementation and opt-in diagnostic report.
- Sets the package and in-app diagnostic report versions to 2.2.1.

These packages are built from the checked-in source and have **not** been
tested on a jailbroken device. The newer R5 route history and temporary
privacy labels in the separate 2.2.1 sideload IPA are not in these DEBs;
that source was not retained.

## Packages

- `dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb` — rootful.
- `dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb` — rootless (`/var/jb`).

SHA-256:

```text
3b055b844046afee71d553d9385cd412e97eeb1b21e2dafa5a068d62900e9ee5  dev.tas.twitchadblock_2.2.1_iphoneos-arm.deb
dd3cfbbb883982347eacd180b9d0fb1388a4b655ff627d79da0ffd275c6aeb6d  dev.tas.twitchadblock_2.2.1_iphoneos-arm64.deb
```
