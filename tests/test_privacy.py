from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include "TASPrivacy.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    char channel[64], same_channel[64], other_channel[64];
    char playlist[64], same_playlist[64], other_playlist[64], segment[64];
    tas_label_channel("privateStreamer", channel, sizeof(channel));
    tas_label_channel("privateStreamer", same_channel, sizeof(same_channel));
    tas_label_channel("someoneElse", other_channel, sizeof(other_channel));
    tas_label_url("https://example.test/privateStreamer/index.m3u8?token=secret", playlist, sizeof(playlist));
    tas_label_url("https://example.test/privateStreamer/index.m3u8?token=secret", same_playlist, sizeof(same_playlist));
    tas_label_url("https://example.test/other.m3u8", other_playlist, sizeof(other_playlist));
    tas_label_url("https://example.test/privateStreamer/segment.ts", segment, sizeof(segment));
    if (strcmp(channel, same_channel) || strcmp(playlist, same_playlist) ||
        !strcmp(channel, other_channel) || !strcmp(playlist, other_playlist) ||
        strncmp(channel, "channel-", 8) || strncmp(playlist, "playlist-", 9) ||
        strncmp(segment, "resource-", 9)) return 1;
    printf("%s %s %s\n", channel, playlist, segment);
    return 0;
}
'''


class PrivacyTests(unittest.TestCase):
    def test_process_local_labels_never_expose_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = root / "privacy.c"
            binary = root / "privacy"
            harness.write_text(HARNESS)
            subprocess.run([
                "cc", "-std=c11", "-D_DEFAULT_SOURCE", "-pthread", "-I", str(ROOT / "src"),
                str(harness), str(ROOT / "src" / "TASPrivacy.c"), "-o", str(binary),
            ], check=True, capture_output=True)
            first = subprocess.run([binary], check=True, capture_output=True, text=True).stdout
            second = subprocess.run([binary], check=True, capture_output=True, text=True).stdout
            self.assertNotIn("privateStreamer", first)
            self.assertNotIn("secret", first)
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
