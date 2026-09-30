#!/usr/bin/env python3
"""Stage the verified R5 IPA with a scoped settings button and clearer copy.

R5's diagnostics source was never committed. This patch deliberately requires
the exact working R5 IPA and changes only its embedded framework binary.
The two ARM64 tail branches go through a small guard in unused executable
padding. It checks the visible controller title, "Settings", before adding
the button. R6's exact runtime-class check excluded the real Settings screen.
"""

from __future__ import annotations

import argparse
import hashlib
import plistlib
import zipfile
from pathlib import Path

from reserve_codesign_space import refresh_adhoc_code_directories
from macho import code_signature
from patch_ipa import update_app_info


R5_IPA_SHA256 = "191d041df0305e03356c3902a57cbc783371998bc15130e3ce46265cc8c1e4a8"
R5_FRAMEWORK_SHA256 = "a9042bae32c0912652e30fbd24fbc92c299e18ceb5c69d345433eb9efda4f3a8"
FRAMEWORK_ENTRY = "Payload/Twitch.app/Frameworks/Tweach.framework/Tweach"
APP_INFO_ENTRY = "Payload/Twitch.app/Info.plist"
APP_DISPLAY_NAME = "Twitch VAFT"

# Executable padding after __eh_frame (ending at 0x122e4), inside the existing
# 16 KiB-aligned __TEXT segment. This is ARM64 code assembled at 0x12300:
#
#   save x19/x20/fp/lr; self = x0
#   title = objc_msgSend(self, sel_registerName("title"))
#   if title == nil: return
#   expected = nsstr("Settings")                 [0x5d34]
#   if !objc_msgSend(title, sel_registerName("isEqualToString:"), expected): return
#   add_ad_block_navigation_item(self)            [0xc87c]
#   restore; return
#
# Both callers have already restored their own stack frames. Branching here
# keeps their original return addresses and leaves every other hook intact.
GUARD_OFFSET = 0x12300
GUARD = bytes.fromhex(
    "f44fbda9fd7b02a9f30300aae0ffffb000cc349199ebff97"
    "e10300aae00313aa84ebff97000200b4f40300aae0ffffb0"
    "00e4349180ceff97e00b00f9e0ffffb000203a918debff97"
    "e20b40f9e10300aae00314aa77ebff9760000036e00313aa"
    "47e9ff97fd7b42a9f44fc3a8c0035fd6"
)
TAIL_BRANCHES = {
    0xC674: (bytes.fromhex("82000014"), bytes.fromhex("23170014")),
    0xCED4: (bytes.fromhex("6afeff17"), bytes.fromhex("0b150014")),
}

OLD_FOOTER = (
    "Records privacy-safe resource aliases, failures, manifest marker summaries, "
    "route history, and VAFT decisions. Channel names, URLs and paths, query "
    "strings, headers, access tokens, and manifest contents are never stored. "
    "Aliases are random per launch. The log is capped at 512 KiB."
).encode()
NEW_FOOTER = (
    "Logging is off by default. When enabled, channel names and playlist URLs "
    "appear as temporary labels (for example, channel-1). Each label stays with "
    "the same channel or playlist until Twitch restarts; then labels reset. "
    "The log holds up to 512 KiB."
).encode()
OLD_REPORT_LINE = (
    "Resource aliases: random per launch; aliases are not comparable across launches."
).encode()
NEW_REPORT_LINE = (
    "Labels stay with the same channel or playlist until Twitch restarts; then reset."
).encode()
OLD_BUILD_LABEL = b"2.2.0-dev-diagnostics-r3"
NEW_BUILD_LABEL = b"2.2.1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_framework(original: bytes) -> bytes:
    if sha256(original) != R5_FRAMEWORK_SHA256:
        raise ValueError("framework is not the known-working R5 binary")
    data = bytearray(original)
    if data[GUARD_OFFSET:GUARD_OFFSET + len(GUARD)] != b"\0" * len(GUARD):
        raise ValueError("executable guard location is occupied")
    data[GUARD_OFFSET:GUARD_OFFSET + len(GUARD)] = GUARD
    for offset, (before, after) in TAIL_BRANCHES.items():
        if data[offset:offset + 4] != before:
            raise ValueError(f"unexpected R5 branch at 0x{offset:x}")
        data[offset:offset + 4] = after

    for old, new in ((OLD_FOOTER, NEW_FOOTER),
                     (OLD_REPORT_LINE, NEW_REPORT_LINE),
                     (OLD_BUILD_LABEL, NEW_BUILD_LABEL)):
        if len(new) > len(old) or data.count(old) != 1:
            raise ValueError("diagnostic copy does not match the R5 baseline")
        at = data.index(old)
        # Report line must retain its exact size: the next line shares a
        # single format string with printf placeholders and other text.
        if old is OLD_REPORT_LINE and len(new) != len(old):
            raise ValueError("report line must keep its original byte length")
        data[at:at + len(old)] = new + b"\0" * (len(old) - len(new))

    signature = code_signature(data)
    if signature is None:
        raise ValueError("R5 framework has no ad-hoc signature")
    refresh_adhoc_code_directories(data, signature[0])
    return bytes(data)


def stage(input_ipa: Path, output_ipa: Path) -> None:
    if input_ipa.resolve() == output_ipa.resolve():
        raise ValueError("output must be separate from the R5 input")
    if sha256(input_ipa.read_bytes()) != R5_IPA_SHA256:
        raise ValueError("input IPA does not match the device-proven R5 package")

    with zipfile.ZipFile(input_ipa, "r") as source, zipfile.ZipFile(output_ipa, "w") as target:
        names = source.namelist()
        if names.count(FRAMEWORK_ENTRY) != 1 or names.count(APP_INFO_ENTRY) != 1:
            raise ValueError("R5 IPA has an unexpected app layout")
        target.comment = source.comment
        for member in source.infolist():
            content = source.read(member.filename)
            if member.filename == FRAMEWORK_ENTRY:
                content = patch_framework(content)
            elif member.filename == APP_INFO_ENTRY:
                content = update_app_info(content)
            target.writestr(member, content)

    with zipfile.ZipFile(input_ipa) as source, zipfile.ZipFile(output_ipa) as staged:
        if source.namelist() != staged.namelist():
            raise ValueError("packaged IPA changed its entry list")
        changes = [name for name in source.namelist() if source.read(name) != staged.read(name)]
        if changes != [APP_INFO_ENTRY, FRAMEWORK_ENTRY]:
            raise ValueError(f"unexpected IPA entry changes: {changes}")
        app_info = plistlib.loads(staged.read(APP_INFO_ENTRY))
        if (
            app_info.get("CFBundleDisplayName") != APP_DISPLAY_NAME
            or app_info.get("CFBundleName") != APP_DISPLAY_NAME
        ):
            raise ValueError("IPA app display name was not updated")
        binary = staged.read(FRAMEWORK_ENTRY)
        if OLD_REPORT_LINE in binary or OLD_FOOTER in binary or OLD_BUILD_LABEL in binary:
            raise ValueError("old diagnostic wording remains")
        if b"Tweach.dylib" in "\n".join(staged.namelist()).encode():
            raise ValueError("obsolete standalone dylib returned")
    print(f"Staged {output_ipa}; changed the app name and framework binary")
    print(f"SHA-256: {sha256(output_ipa.read_bytes())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-reproduction", action="store_true",
                        help="explicitly reproduce the archived 2.2.1 binary, never a current release")
    parser.add_argument("r5_ipa", type=Path)
    parser.add_argument("output_ipa", type=Path)
    args = parser.parse_args()
    if not args.historical_reproduction:
        parser.error("archived R5 reproducer; use patch_ipa.py for current builds")
    stage(args.r5_ipa, args.output_ipa)


if __name__ == "__main__":
    main()
