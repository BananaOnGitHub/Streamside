from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include "TASEmoteGeometry.h"
#include <assert.h>
int main(void) {
    const unsigned char gif[] = "GIF89a\x70\x00\x1c\x00";
    unsigned char png[24] = "\211PNG\r\n\032\n\0\0\0\15IHDR";
    png[19] = 56; png[23] = 112;
    unsigned char webp[30] = "RIFF\0\0\0\0WEBPVP8X";
    webp[24] = 111; webp[27] = 27;
    unsigned char lossless[25] = "RIFF\0\0\0\0WEBPVP8L";
    lossless[20] = 0x2f; lossless[21] = 111; lossless[22] = 0xc0; lossless[23] = 6;
    unsigned char lossy[30] = "RIFF\0\0\0\0WEBPVP8 ";
    lossy[23] = 0x9d; lossy[24] = 1; lossy[25] = 0x2a; lossy[26] = 112; lossy[28] = 28;
    assert(tas_emote_image_aspect(gif, 10) == 4);
    assert(tas_emote_image_aspect(png, 24) == 0.5);
    assert(tas_emote_image_aspect(webp, 30) == 4);
    assert(tas_emote_image_aspect(lossless, 25) == 4);
    assert(tas_emote_image_aspect(lossy, 30) == 4);
    for (size_t n = 0; n < 10; n++) assert(!tas_emote_image_aspect(gif,n));
    for (size_t n = 0; n < 24; n++) assert(!tas_emote_image_aspect(png,n));
    for (size_t n = 0; n < 30; n++) assert(!tas_emote_image_aspect(webp,n));
    for (size_t n = 0; n < 25; n++) assert(!tas_emote_image_aspect(lossless,n));
    assert(!tas_emote_image_aspect(NULL, 100));
    png[16] = 255; assert(!tas_emote_image_aspect(png,24));
    double w = 28, h = 28;
    tas_emote_proportions(&w,&h,4); assert(w == 112 && h == 28);
    tas_emote_proportions(&w,&h,4); assert(w == 112 && h == 28);
    w = h = 28; tas_emote_proportions(&w,&h,0.5); assert(w == 14 && h == 28);
    w = h = 28; tas_emote_proportions(&w,&h,10); assert(w == 140 && h == 14);
    for (int i = 0; i < 20; i++) tas_emote_proportions(&w,&h,10);
    assert(w == 140 && h == 14);
    tas_emote_proportions(&w,&h,0); assert(w == 140 && h == 14);
    return 0;
}
'''


class EmoteGeometryTests(unittest.TestCase):
    def test_provider_headers_and_repeated_native_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = Path(directory) / "geometry.c"
            binary = Path(directory) / "geometry"
            harness.write_text(HARNESS)
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
                            "-I", str(ROOT / "src"), str(harness), "-o", str(binary)],
                           check=True, capture_output=True)
            # The sandbox restricts /proc task enumeration used by LeakSanitizer.
            # Keep address/undefined checks enabled; this harness allocates nothing.
            subprocess.run([binary], check=True, capture_output=True,
                           env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
