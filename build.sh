#!/bin/sh
set -eu

cd "$(dirname "$0")"

ZIG="${ZIG:-$(command -v zig || true)}"
if [ -z "$ZIG" ]; then
    echo "error: Zig 0.14.0 is required (set ZIG=/path/to/zig)" >&2
    exit 1
fi

ZIG_REAL="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$ZIG")"
ZIG_LIB="${ZIG_LIB:-$(dirname "$ZIG_REAL")/lib}"
IOS_STUBS="${IOS_STUBS:-$PWD/stubs}"
LOCAL_CACHE="${ZIG_LOCAL_CACHE_DIR:-$PWD/build/cache}"
GLOBAL_CACHE="${ZIG_GLOBAL_CACHE_DIR:-$PWD/build/global-cache}"
EMOTE_DIAGNOSTIC="${EMOTE_DIAGNOSTIC:-0}"
IMAGE_DEMAND_DIAGNOSTIC="${IMAGE_DEMAND_DIAGNOSTIC:-0}"
case "$IMAGE_DEMAND_DIAGNOSTIC" in 0|1) ;; *) echo 'IMAGE_DEMAND_DIAGNOSTIC must be 0 or 1' >&2; exit 1 ;; esac
case "$EMOTE_DIAGNOSTIC" in 0|1) ;; *) echo 'EMOTE_DIAGNOSTIC must be 0 or 1' >&2; exit 1 ;; esac

mkdir -p build "$LOCAL_CACHE" "$GLOBAL_CACHE"

build_binary() {
    output_path="$1"
    install_name="$2"
    binary_name="$3"
    ZIG_LOCAL_CACHE_DIR="$LOCAL_CACHE" \
    ZIG_GLOBAL_CACHE_DIR="$GLOBAL_CACHE" \
    "$ZIG" build-lib \
      -target aarch64-ios-none \
      -O ReleaseSmall -dynamic -fPIC -fno-stack-protector \
      -isystem "$ZIG_LIB/libc/include/any-macos-any" \
      -L"$IOS_STUBS" -lSystem -lobjc \
      -install_name "$install_name" \
      -dead_strip -headerpad 4000 \
      --entitlements entitlements.plist \
      --name "$binary_name" \
      -femit-bin="$output_path" \
      -cflags -Wall -Wextra -Werror -fblocks -fvisibility=hidden "-DTAS_EMOTE_DIAGNOSTIC=$EMOTE_DIAGNOSTIC" "-DTAS_IMAGE_DEMAND_DIAGNOSTIC=$IMAGE_DEMAND_DIAGNOSTIC" -- \
      src/Streamside.c src/TASDiagnostics.c src/TASPrivacy.c src/TASEmotes.c src/TASEmoteUI.c src/TASEmotePresentation.c src/TASEmoteImageProbe.c src/SSComposer.c src/TASRNComposerUI.c src/TASImageDemand.c
}

# Jailbreak package: keep the clean identity and a large in-place signature
# reservation for injection frameworks that replace the ad-hoc signature.
build_binary build/Streamside.dylib @rpath/Streamside.dylib Streamside
python3 tools/align_macho_segments.py build/Streamside.dylib
python3 tools/reserve_codesign_space.py build/Streamside.dylib --size 65536
python3 tools/artifact_guard.py record build/Streamside.dylib

# Sideload package: clean identity, same normalized layout as the working build.
# Record a fingerprint ONLY after normalization, compaction and validation.
mkdir -p build/Streamside.framework
build_binary build/Streamside.framework/Streamside @rpath/Streamside.framework/Streamside Streamside
python3 tools/align_macho_segments.py build/Streamside.framework/Streamside
python3 tools/shrink_adhoc_signature.py build/Streamside.framework/Streamside
cp packaging/StreamsideFramework-Info.plist build/Streamside.framework/Info.plist
python3 tools/artifact_guard.py record build/Streamside.framework --framework
