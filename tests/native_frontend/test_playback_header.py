"""Compile the shared retained-result boundary as both C and ARC Objective-C."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class PlaybackHeader(unittest.TestCase):
    def test_c_and_arc_objective_c_ownership_declarations(self):
        zig=os.environ.get('ZIG') or shutil.which('zig')
        self.assertTrue(zig,'Pinned Zig is required for the host compile check')
        executable=Path(zig).resolve()
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'caller.c'
            source.write_text('#include "SSNPlaybackRequest.h"\n#include "SSNContentLabelsRequest.h"\nvoid use(void) { id result=ssn_playback_request_variant((id)0,(id)0,(id)0); (void)result; id labels=ssn_content_labels_request((id)0); (void)labels; }\n')
            for language in ['c','objective-c']:
                with self.subTest(language=language):
                    result=subprocess.run([str(executable),'cc','-target','aarch64-ios-none',
                        '-isystem',str(executable.parent/'lib/libc/include/any-macos-any'),
                        '-Wall','-Wextra','-Werror','-c','-x',language,
                        *(['-fobjc-arc'] if language=='objective-c' else []),
                        '-I'+str(ROOT/'native'),str(source),'-o',str(Path(folder)/(language+'.o'))],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
