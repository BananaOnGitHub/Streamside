# 2.2.1 sideload release staging

Historical reproduction only: the script requires `--historical-reproduction`.
It is not a current release path. Use the fingerprint-checked `patch_ipa.py`
with `Streamside.framework` for current builds.

This page records how the earlier 2.2.1 binary was staged. The source-backed
replacement reconstructs these diagnostics in `src/` and builds both formats
from source.

The source for the R5 privacy and route-history diagnostics was built for a
device-tested IPA but was not committed to this repository. The native
diagnostics implementation still derives from the August 21 `8c8b543`
baseline. Do not rebuild it and claim that its output includes the R5
diagnostics.

`tools/stage_r5_production.py` takes the exact device-tested R5 IPA (SHA-256
`191d041df0305e03356c3902a57cbc783371998bc15130e3ce46265cc8c1e4a8`)
and writes a separate candidate. It refuses another input. Only
`Payload/Twitch.app/Frameworks/Tweach.framework/Tweach` changes. The patch:

- Shows the settings button only when the visible controller title is
  `Settings`. The R6 exact-class guard hid it from the actual Settings screen
  in a device test; R7 restores that screen while excluding Chat Identity.
- Explains temporary diagnostic labels in the settings footer and report.
- Sets the in-app port-build label to `2.2.1`.
- Updates the existing ad-hoc CodeDirectory hashes without changing its size,
  executable range, or 16 KiB segment geometry.

The same UI scope fix is applied to `src/TASDiagnostics.c` for future source
builds. Its older diagnostics implementation does not yet include R5's privacy
and route-history work. Restore those source changes before treating a source
build as a replacement for the R5 candidate.

R6 failed on device because its exact-class guard also hid the main Settings
button. R7 was confirmed on device to restore the Settings entry. The 2.2.1
IPA uses the same code as R7 and changes its build label. The title guard
currently recognizes the English `Settings` title.

The IPA release is **sideload only**. The separate 2.2.1-jb prerelease is built
from the repository's older diagnostics source with the Settings button fix;
it lacks the R5 privacy and route changes. The exact R5 diagnostics source is
unavailable, and this staging script needs the specific R5 IPA above as input.
